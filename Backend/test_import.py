try:
    from filtering_routes import filtering_blueprint
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
