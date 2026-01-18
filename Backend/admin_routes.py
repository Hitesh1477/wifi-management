 #pip install pandas openpyxl xlrd

from flask import Blueprint, request, jsonify, current_app as app
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from pymongo import MongoClient
import jwt, datetime
from bson.objectid import ObjectId
import pandas as pd
import io

# ✅ MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
admins_collection = db['admins']
users_collection = db['users']
web_filter_collection = db['web_filter']

# ✅ Middleware for token check
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({"message": "Token missing"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            if data.get("role") != "admin":
                return jsonify({"message": "Unauthorized"}), 403

        except Exception:
            return jsonify({"message": "Invalid or expired token"}), 401

        return f(*args, **kwargs)
    return decorated

admin_routes = Blueprint("admin_routes", __name__)

def _find_user_by_mixed_id(id):
    try:
        oid = ObjectId(id)
        doc = users_collection.find_one({"_id": oid})
        if doc:
            return doc
    except Exception:
        pass
    doc = users_collection.find_one({"_id": id})
    if doc:
        return doc
    doc = users_collection.find_one({"roll_no": id})
    return doc

# ✅ Admin Login
@admin_routes.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    admin = admins_collection.find_one({"username": username})

    if not admin or not check_password_hash(admin["password"], password):
        return jsonify({"message": "Invalid admin credentials"}), 401

    token = jwt.encode({
        "username": username,
        "role": "admin",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"message": "Admin login successful", "token": token})

@admin_routes.route("/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    total_users = users_collection.count_documents({})
    active_users = users_collection.count_documents({"status": "online"})  # later when tracking usage
    blocked_users = users_collection.count_documents({"blocked": True})

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users
    }), 200

@admin_routes.route('/admin/clients', methods=['GET'])
@admin_required
def admin_clients():
    """Return list of non-admin users with their latest activity from detections"""
    try:
        clients_cursor = users_collection.find({"role": {"$ne": "admin"}}, {"password": 0})
        clients = []
        
        # Get collections
        detections_col = db['detections'] if 'detections' in db.list_collection_names() else None
        blocked_users_col = db['blocked_users'] if 'blocked_users' in db.list_collection_names() else None
        active_sessions_col = db['active_sessions'] if 'active_sessions' in db.list_collection_names() else None
        
        for c in clients_cursor:
            c['_id'] = str(c.get('_id'))
            roll_no = c.get('roll_no')
            
            # Check if user is blocked in blocked_users collection
            is_blocked = False
            block_status = None
            block_details = None
            
            if blocked_users_col is not None and roll_no:
                block_doc = blocked_users_col.find_one({"roll_no": roll_no, "status": "blocked"})
                if block_doc:
                    is_blocked = True
                    ban_type = block_doc.get("ban_type", "temporary")
                    expires_at = block_doc.get("expires_at")
                    
                    if ban_type == "permanent":
                        block_status = "Blocked (permanent)"
                    elif expires_at:
                        # Show expiry time for temporary bans
                        import pytz
                        ist = pytz.timezone('Asia/Kolkata')
                        # Convert UTC to IST
                        if hasattr(expires_at, 'replace'):
                            expires_at_utc = expires_at.replace(tzinfo=pytz.utc)
                            expires_at_ist = expires_at_utc.astimezone(ist)
                            expiry_str = expires_at_ist.strftime('%I:%M %p, %d %b')
                            block_status = f"Blocked until {expiry_str}"
                        else:
                            block_status = f"Blocked (temporary)"
                    else:
                        block_status = f"Blocked (temporary)"
                    
                    block_details = {
                        "reason": block_doc.get("reason", "No reason provided"),
                        "confidence": block_doc.get("confidence", 0),
                        "blocked_at": block_doc.get("blocked_at")
                    }
            
            # Determine status
            if is_blocked:
                # User is blocked
                c['status'] = block_status
                c['blocked'] = True
                if block_details:
                    c['block_details'] = block_details
            else:
                # Check if user has active session
                has_active_session = False
                if active_sessions_col is not None and roll_no:
                    session = active_sessions_col.find_one({"roll_no": roll_no, "status": "active"})
                    if session:
                        has_active_session = True
                        c['ip_address'] = session.get('client_ip', 'N/A')
                
                if has_active_session:
                    c['status'] = "Online"
                else:
                    c['status'] = "Offline"
                
                c['blocked'] = False
            
            # Get IP from active session if not already set
            if not c.get('ip_address'):
                if active_sessions_col is not None and roll_no:
                    session = active_sessions_col.find_one({"roll_no": roll_no, "status": "active"})
                    if session:
                        c['ip_address'] = session.get('client_ip', 'N/A')
                    else:
                        c['ip_address'] = c.get('ip_address', 'N/A')
                else:
                    c['ip_address'] = c.get('ip_address', 'N/A')
            
            # Get latest activity from detections
            if detections_col is not None and roll_no:
                try:
                    # Get most recent detection for this user
                    latest = detections_col.find_one(
                        {"roll_no": roll_no}, 
                        sort=[("timestamp", -1)]
                    )
                    if latest:
                        c['activity'] = f"{latest.get('app_name', 'Unknown')} ({latest.get('domain', 'N/A')})"
                    else:
                        c['activity'] = c.get('activity', 'Idle')
                    
                    # Count detections as rough "data usage" (number of requests)
                    detection_count = detections_col.count_documents({"roll_no": roll_no})
                    c['data_usage'] = round(detection_count * 0.01, 2)
                except Exception:
                    c['activity'] = c.get('activity', 'Idle')
                    c['data_usage'] = 0
            else:
                c['activity'] = c.get('activity', 'Idle')
                c['data_usage'] = 0
            
            clients.append(c)
        
        return jsonify({"clients": clients}), 200
    except Exception as e:
        print(f"Error in admin_clients: {e}")
        return jsonify({"error": str(e), "clients": []}), 500

@admin_routes.route('/admin/clients', methods=['POST'])
@admin_required
def admin_add_client():
    data = request.get_json() or {}
    roll_no = (data.get('roll_no') or '').strip()
    password = (data.get('password') or '').strip()
    activity = (data.get('activity') or '').strip() or 'Idle'

    if not roll_no:
        return jsonify({"message": "roll_no required"}), 400
    if users_collection.find_one({"roll_no": roll_no}):
        return jsonify({"message": "User already exists"}), 409

    doc = {
        "roll_no": roll_no,
        "role": "student",
        "blocked": False,
        "activity": activity,
    }
    if password:
        doc["password"] = generate_password_hash(password)

    inserted = users_collection.insert_one(doc)
    return jsonify({"message": "Client added", "id": str(inserted.inserted_id)}), 201

@admin_routes.route('/admin/clients/<id>', methods=['GET'])
@admin_required
def admin_get_client(id):
    c = _find_user_by_mixed_id(id)
    if not c:
        return jsonify({"message": "Not found"}), 404
    c['_id'] = str(c['_id'])
    return jsonify({"client": c}), 200

@admin_routes.route('/admin/clients/<id>', methods=['PATCH'])
@admin_required
def admin_update_client(id):
    doc = _find_user_by_mixed_id(id)
    if not doc:
        return jsonify({"message": "Not found"}), 404
    oid = doc.get('_id')
    roll_no = doc.get('roll_no')
    data = request.get_json() or {}

    updates = {}
    if 'roll_no' in data and isinstance(data['roll_no'], str) and data['roll_no'].strip():
        new_roll = data['roll_no'].strip()
        # prevent duplicate roll_no
        existing = users_collection.find_one({"roll_no": new_roll, "_id": {"$ne": oid}})
        if existing:
            return jsonify({"message": "roll_no already in use"}), 409
        updates['roll_no'] = new_roll

    if 'password' in data and isinstance(data['password'], str) and data['password'].strip():
        updates['password'] = generate_password_hash(data['password'].strip())

    # Handle blocking/unblocking - write to blocked_users collection
    if 'blocked' in data:
        should_block = bool(data['blocked'])
        updates['blocked'] = should_block
        
        blocked_users_col = db['blocked_users']
        
        if should_block:
            # Block the user - add to blocked_users collection
            blocked_users_col.update_one(
                {"roll_no": roll_no},
                {
                    "$set": {
                        "roll_no": roll_no,
                        "ban_type": "permanent",  # Admin blocks are permanent by default
                        "confidence": 1.0,
                        "reason": "Manually blocked by admin",
                        "blocked_at": datetime.datetime.utcnow(),
                        "expires_at": None,
                        "status": "blocked"
                    }
                },
                upsert=True
            )
        else:
            # Unblock the user - remove from blocked_users collection
            blocked_users_col.delete_one({"roll_no": roll_no})

    if 'activity' in data and isinstance(data['activity'], str):
        updates['activity'] = data['activity']

    # Handle bandwidth_limit - can be string (preset) or number (custom Mbps)
    if 'bandwidth_limit' in data:
        updates['bandwidth_limit'] = data['bandwidth_limit']

    if not updates:
        return jsonify({"message": "No changes"}), 400

    res = users_collection.update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        return jsonify({"message": "Not found"}), 404
    return jsonify({"message": "Client updated"}), 200


@admin_routes.route('/admin/logs', methods=['GET'])
@admin_required
def admin_logs():
    """Return network activity logs from the detections collection"""
    logs = []
    
    # Get detections from the detections collection
    if 'detections' in db.list_collection_names():
        detections_cursor = db['detections'].find().sort([('timestamp', -1)]).limit(100)
        for d in detections_cursor:
            # Format timestamp
            ts = d.get('timestamp')
            if ts:
                time_str = ts.strftime('%I:%M:%S %p') if hasattr(ts, 'strftime') else str(ts)
            else:
                time_str = 'N/A'
            
            # Determine log level based on category
            category = d.get('category', 'general').lower()
            if category in ('proxy', 'vpn', 'adult', 'malware'):
                level = 'error'
            elif category in ('gaming', 'streaming', 'social'):
                level = 'warn'
            else:
                level = 'info'
            
            logs.append({
                '_id': str(d.get('_id')),
                'time': time_str,
                'level': level,
                'user': d.get('roll_no', 'Unknown'),
                'ip': d.get('client_ip', 'N/A'),
                'action': f"Accessed {d.get('domain', 'unknown')} ({d.get('app_name', 'Unknown')})",
                'domain': d.get('domain'),
                'category': d.get('category', 'general'),
                'app_name': d.get('app_name', 'Unknown')
            })
    
    return jsonify({"logs": logs}), 200


@admin_routes.route('/admin/reports', methods=['POST'])
@admin_required
def admin_reports():
    """Generate reports from real detection data"""
    data = request.get_json() or {}
    report_type = data.get('type', 'Top Bandwidth Users')
    time_range = data.get('range', 'weekly')
    
    try:
        detections_col = db['detections'] if 'detections' in db.list_collection_names() else None
        
        # Calculate time filter based on range
        now = datetime.datetime.utcnow()
        if time_range == 'daily':
            start_date = now - datetime.timedelta(days=1)
        elif time_range == 'weekly':
            start_date = now - datetime.timedelta(weeks=1)
        else:  # monthly
            start_date = now - datetime.timedelta(days=30)
        
        headers = []
        rows = []
        
        if report_type == 'Top Bandwidth Users':
            headers = ['Rank', 'Student ID', 'Requests Count', 'Top Domain']
            
            if detections_col is not None:
                # Aggregate detections by roll_no
                pipeline = [
                    {"$match": {"timestamp": {"$gte": start_date}}},
                    {"$group": {
                        "_id": "$roll_no",
                        "count": {"$sum": 1},
                        "domains": {"$push": "$domain"}
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
                results = list(detections_col.aggregate(pipeline))
                
                for i, r in enumerate(results):
                    # Find most common domain
                    domains = r.get('domains', [])
                    top_domain = max(set(domains), key=domains.count) if domains else 'N/A'
                    rows.append([
                        f"#{i+1}",
                        r.get('_id', 'Unknown'),
                        str(r.get('count', 0)),
                        top_domain
                    ])
        
        elif report_type == 'Blocked Site Activity':
            headers = ['Domain', 'Category', 'Access Count', 'Users']
            
            if detections_col is not None:
                # Aggregate by domain and category
                pipeline = [
                    {"$match": {"timestamp": {"$gte": start_date}}},
                    {"$group": {
                        "_id": {"domain": "$domain", "category": "$category"},
                        "count": {"$sum": 1},
                        "users": {"$addToSet": "$roll_no"}
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 20}
                ]
                results = list(detections_col.aggregate(pipeline))
                
                for r in results:
                    domain = r.get('_id', {}).get('domain', 'Unknown')
                    category = r.get('_id', {}).get('category', 'general')
                    users = r.get('users', [])
                    rows.append([
                        domain,
                        category,
                        str(r.get('count', 0)),
                        ', '.join(users[:3]) + ('...' if len(users) > 3 else '')
                    ])
        
        elif report_type == 'Full Network Audit':
            headers = ['Time', 'Student', 'IP', 'Domain', 'Category']
            
            if detections_col is not None:
                # Get recent detections
                detections = list(detections_col.find(
                    {"timestamp": {"$gte": start_date}}
                ).sort([("timestamp", -1)]).limit(50))
                
                for d in detections:
                    ts = d.get('timestamp')
                    time_str = ts.strftime('%Y-%m-%d %H:%M') if hasattr(ts, 'strftime') else str(ts)[:16]
                    rows.append([
                        time_str,
                        d.get('roll_no', 'Unknown'),
                        d.get('client_ip', 'N/A'),
                        d.get('domain', 'N/A'),
                        d.get('category', 'general')
                    ])
        
        return jsonify({
            "headers": headers,
            "data": rows,
            "title": f"{time_range.capitalize()} {report_type}",
            "generated_at": now.isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({"error": str(e), "headers": [], "data": []}), 500

@admin_routes.route('/admin/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload_clients():
    """Bulk upload students via CSV/Excel file"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload CSV or Excel file'}), 400
        
        # Read file
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(file.stream.read().decode('utf-8')))
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return jsonify({'error': f'Failed to read file: {str(e)}'}), 400
        
        # Validate columns
        required_columns = ['roll_number', 'password']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': f'CSV must contain columns: {", ".join(required_columns)}'}), 400
        
        # Remove NaN values
        df = df.dropna(subset=required_columns)
        
        added_count = 0
        skipped_count = 0
        errors = []
        
        # Process each row
        for index, row in df.iterrows():
            roll_no = str(row['roll_number']).strip()
            password = str(row['password']).strip()
            
            if not roll_no or not password:
                skipped_count += 1
                errors.append(f'Row {index + 2}: Missing data')
                continue
            
            # Check if student exists
            if users_collection.find_one({'roll_no': roll_no}):
                skipped_count += 1
                errors.append(f'Student {roll_no} already exists')
                continue
            
            # Insert new student (using same structure as existing add_client route)
            doc = {
                'roll_no': roll_no,
                'password': generate_password_hash(password),
                'role': 'student',
                'blocked': False,
                'activity': 'Idle',
            }
            
            users_collection.insert_one(doc)
            added_count += 1
        
        return jsonify({
            'message': 'Bulk upload completed',
            'added': added_count,
            'skipped': skipped_count,
            'errors': errors[:10]
        }), 200
        
    except Exception as e:
        print(f"Bulk upload error: {e}")
        return jsonify({'error': str(e)}), 500 
 #   � S&   W e b   F i l t e r i n g  
 D E F A U L T _ C A T E G O R I E S   =   {  
         " G a m i n g " :   {  
                 " a c t i v e " :   T r u e ,  
                 " s i t e s " :   [ " s t e a m p o w e r e d . c o m " ,   " t w i t c h . t v " ,   " r o b l o x . c o m " ,   " d i s c o r d . g g " ,   " e p i c g a m e s . c o m " ,   " e a . c o m " ,   " p l a y v a l o r a n t . c o m " ,   " m i n e c r a f t . n e t " ,   " b a t t l e . n e t " ,   " u b i s o f t . c o m " ]  
         } ,  
         " S o c i a l   M e d i a " :   {  
                 " a c t i v e " :   F a l s e ,  
                 " s i t e s " :   [ " t i k t o k . c o m " ,   " i n s t a g r a m . c o m " ,   " f a c e b o o k . c o m " ,   " t w i t t e r . c o m " ,   " r e d d i t . c o m " ,   " s n a p c h a t . c o m " ,   " p i n t e r e s t . c o m " ]  
         } ,  
         " S t r e a m i n g " :   {  
                 " a c t i v e " :   F a l s e ,  
                 " s i t e s " :   [ " n e t f l i x . c o m " ,   " h u l u . c o m " ,   " d i s n e y p l u s . c o m " ,   " h b o m a x . c o m " ,   " p r i m e v i d e o . c o m " ,   " s p o t i f y . c o m " ,   " p e a c o c k t v . c o m " ]  
         } ,  
         " F i l e   S h a r i n g " :   {  
                 " a c t i v e " :   T r u e ,  
                 " s i t e s " :   [ " t h e p i r a t e b a y . o r g " ,   " 1 3 3 7 x . t o " ,   " m e g a u p l o a d . c o m " ,   " w e t r a n s f e r . c o m " ,   " m e d i a f i r e . c o m " ,   " r a r b g . t o " ]  
         } ,  
         " P r o x y / V P N " :   {  
                 " a c t i v e " :   T r u e ,  
                 " s i t e s " :   [ " n o r d v p n . c o m " ,   " e x p r e s s v p n . c o m " ,   " h i d e m y a s s . c o m " ,   " p r o x y s i t e . c o m " ,   " c y b e r g h o s t v p n . c o m " ,   " s u r f s h a r k . c o m " ,   " p r i v a t e i n t e r n e t a c c e s s . c o m " ,   " p r o t o n v p n . m e " ,   " t u n n e l b e a r . c o m " ]  
         }  
 }  
  
 d e f   _ r e f r e s h _ w e b _ f i l t e r _ d e f a u l t s ( ) :  
         " " " E n s u r e   b a s i c   s t r u c t u r e   e x i s t s   i n   D B " " "  
         i f   w e b _ f i l t e r _ c o l l e c t i o n . c o u n t _ d o c u m e n t s ( { } )   = =   0 :  
                 #   I n i t i a l i z e   d e f a u l t   s t r u c t u r e  
                 d o c   =   {  
                         " t y p e " :   " c o n f i g " ,  
                         " c a t e g o r i e s " :   D E F A U L T _ C A T E G O R I E S ,  
                         " m a n u a l _ b l o c k s " :   [ " s p e c i f i c - c h e a t i n g - s i t e . c o m " ,   " u n b l o c k - p r o x y . n e t " ]  
                 }  
                 w e b _ f i l t e r _ c o l l e c t i o n . i n s e r t _ o n e ( d o c )  
  
 @ a d m i n _ r o u t e s . r o u t e ( ' / a d m i n / f i l t e r i n g ' ,   m e t h o d s = [ ' G E T ' ] )  
 @ a d m i n _ r e q u i r e d  
 d e f   g e t _ f i l t e r i n g ( ) :  
         _ r e f r e s h _ w e b _ f i l t e r _ d e f a u l t s ( )  
         c o n f i g   =   w e b _ f i l t e r _ c o l l e c t i o n . f i n d _ o n e ( { " t y p e " :   " c o n f i g " } )  
         i f   n o t   c o n f i g :  
                 r e t u r n   j s o n i f y ( { " m e s s a g e " :   " E r r o r   l o a d i n g   c o n f i g " } ) ,   5 0 0  
          
         r e t u r n   j s o n i f y ( {  
                 " c a t e g o r i e s " :   c o n f i g . g e t ( " c a t e g o r i e s " ,   { } ) ,  
                 " m a n u a l _ b l o c k s " :   c o n f i g . g e t ( " m a n u a l _ b l o c k s " ,   [ ] )  
         } ) ,   2 0 0  
  
 @ a d m i n _ r o u t e s . r o u t e ( ' / a d m i n / f i l t e r i n g / c a t e g o r i e s ' ,   m e t h o d s = [ ' P O S T ' ] )  
 @ a d m i n _ r e q u i r e d  
 d e f   t o g g l e _ c a t e g o r y ( ) :  
         d a t a   =   r e q u e s t . g e t _ j s o n ( )  
         c a t e g o r y   =   d a t a . g e t ( " c a t e g o r y " )  
          
         i f   n o t   c a t e g o r y :  
                 r e t u r n   j s o n i f y ( { " m e s s a g e " :   " C a t e g o r y   r e q u i r e d " } ) ,   4 0 0  
                  
         _ r e f r e s h _ w e b _ f i l t e r _ d e f a u l t s ( )  
         c o n f i g   =   w e b _ f i l t e r _ c o l l e c t i o n . f i n d _ o n e ( { " t y p e " :   " c o n f i g " } )  
          
         c a t e g o r i e s   =   c o n f i g . g e t ( " c a t e g o r i e s " ,   { } )  
         i f   c a t e g o r y   n o t   i n   c a t e g o r i e s :  
                 r e t u r n   j s o n i f y ( { " m e s s a g e " :   " C a t e g o r y   n o t   f o u n d " } ) ,   4 0 4  
                  
         #   T o g g l e  
         c u r r e n t _ s t a t u s   =   c a t e g o r i e s [ c a t e g o r y ] [ " a c t i v e " ]  
         n e w _ s t a t u s   =   n o t   c u r r e n t _ s t a t u s  
          
         w e b _ f i l t e r _ c o l l e c t i o n . u p d a t e _ o n e (  
                 { " t y p e " :   " c o n f i g " } ,  
                 { " $ s e t " :   { f " c a t e g o r i e s . { c a t e g o r y } . a c t i v e " :   n e w _ s t a t u s } }  
         )  
          
         r e t u r n   j s o n i f y ( { " m e s s a g e " :   " U p d a t e d " ,   " a c t i v e " :   n e w _ s t a t u s } ) ,   2 0 0  
  
 @ a d m i n _ r o u t e s . r o u t e ( ' / a d m i n / f i l t e r i n g / s i t e s ' ,   m e t h o d s = [ ' P O S T ' ] )  
 @ a d m i n _ r e q u i r e d  
 d e f   a d d _ b l o c k e d _ s i t e ( ) :  
         d a t a   =   r e q u e s t . g e t _ j s o n ( )  
         u r l   =   d a t a . g e t ( " u r l " )  
          
         i f   n o t   u r l :  
                 r e t u r n   j s o n i f y ( { " m e s s a g e " :   " U R L   r e q u i r e d " } ) ,   4 0 0  
                  
         _ r e f r e s h _ w e b _ f i l t e r _ d e f a u l t s ( )  
          
         #   C h e c k   i f   a l r e a d y   e x i s t s  
         c o n f i g   =   w e b _ f i l t e r _ c o l l e c t i o n . f i n d _ o n e ( { " t y p e " :   " c o n f i g " } )  
         i f   u r l   i n   c o n f i g . g e t ( " m a n u a l _ b l o c k s " ,   [ ] ) :  
                   r e t u r n   j s o n i f y ( { " m e s s a g e " :   " A l r e a d y   b l o c k e d " } ) ,   4 0 9  
                    
         w e b _ f i l t e r _ c o l l e c t i o n . u p d a t e _ o n e (  
                 { " t y p e " :   " c o n f i g " } ,  
                 { " $ p u s h " :   { " m a n u a l _ b l o c k s " :   u r l } }  
         )  
          
         r e t u r n   j s o n i f y ( { " m e s s a g e " :   " S i t e   b l o c k e d " } ) ,   2 0 1  
  
 @ a d m i n _ r o u t e s . r o u t e ( ' / a d m i n / f i l t e r i n g / s i t e s ' ,   m e t h o d s = [ ' D E L E T E ' ] )  
 @ a d m i n _ r e q u i r e d  
 d e f   r e m o v e _ b l o c k e d _ s i t e ( ) :  
         d a t a   =   r e q u e s t . g e t _ j s o n ( )  
         u r l   =   d a t a . g e t ( " u r l " )  
          
         i f   n o t   u r l :  
                 r e t u r n   j s o n i f y ( { " m e s s a g e " :   " U R L   r e q u i r e d " } ) ,   4 0 0  
                  
         _ r e f r e s h _ w e b _ f i l t e r _ d e f a u l t s ( )  
          
         w e b _ f i l t e r _ c o l l e c t i o n . u p d a t e _ o n e (  
                 { " t y p e " :   " c o n f i g " } ,  
                 { " $ p u l l " :   { " m a n u a l _ b l o c k s " :   u r l } }  
         )  
          
         r e t u r n   j s o n i f y ( { " m e s s a g e " :   " S i t e   u n b l o c k e d " } ) ,   2 0 0  
 