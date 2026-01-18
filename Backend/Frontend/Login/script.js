// ✅ Login Function
function loginUser() {
    const roll_no = document.getElementById("roll_no").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!roll_no || !password) {
        document.getElementById("error").innerText = "Please enter both fields";
        return;
    }

    // ✅ Use relative URL for LAN compatibility
    fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roll_no, password })
    })
    .then(res => res.json())
    .then(data => {
        console.log("Response:", data);

        if (data.token) {
            // ✅ Save login session
            localStorage.setItem("token", data.token);
            localStorage.setItem("roll_no", roll_no);

            // ✅ Redirect after login success
            window.location.href = "/home";
        } else {
            document.getElementById("error").innerText = data.msg || "Invalid credentials";
        }
    })
    .catch(err => {
        console.error(err);
        document.getElementById("error").innerText = "Server error";
    });
}

// ✅ Logout function
function logoutUser() {
    const roll_no = localStorage.getItem("roll_no");
    
    // Clear local storage first
    localStorage.removeItem("token");
    localStorage.removeItem("roll_no");
    
    // ✅ Call backend to delete session, then redirect
    if (roll_no) {
        fetch("/api/auth/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ roll_no })
        })
        .then(() => {
            console.log("Session deleted on server");
            // Redirect to login page
            window.location.replace(window.location.origin + "/");
        })
        .catch(err => {
            console.error("Logout error:", err);
            // Redirect anyway even if logout fails
            window.location.replace(window.location.origin + "/");
        });
    } else {
        // No roll_no, just redirect
        window.location.replace(window.location.origin + "/");
    }
}

