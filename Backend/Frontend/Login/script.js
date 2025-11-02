// ✅ Login Function
function loginUser() {
    const roll_no = document.getElementById("roll_no").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!roll_no || !password) {
        document.getElementById("error").innerText = "Please enter both fields";
        return;
    }

    fetch("http://127.0.0.1:5000/login", {
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
            window.location.href = "home.html";
        } else {
            document.getElementById("error").innerText = "Invalid credentials";
        }
    })
    .catch(err => {
        console.error(err);
        document.getElementById("error").innerText = "Server error";
    });
}

// ✅ Logout function (use in future)
function logoutUser() {
    localStorage.removeItem("token");
    localStorage.removeItem("roll_no");
    window.location.href = "index.html";
}
