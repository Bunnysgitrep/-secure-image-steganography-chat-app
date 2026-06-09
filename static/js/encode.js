
document.addEventListener("DOMContentLoaded", function(){

    // ===== SECRET MESSAGE COUNT =====
    const secretInput = document.getElementById("secretMessage");
    const charCount = document.getElementById("charCount");

    if(secretInput && charCount){
        secretInput.addEventListener("input", function(){
            charCount.textContent = this.value.length;
        })
    }

    // ===== PASSWORD VALIDATION =====
    const password = document.getElementById("password");
    const passCount = document.getElementById("passCount");

    const lower = document.getElementById("lower");
    const upper = document.getElementById("upper");
    const number = document.getElementById("number");
    const special = document.getElementById("special");
    const lengthRule = document.getElementById("length");

    if(password){
        password.addEventListener("input", function(){

            const value = password.value;

            if(passCount) passCount.textContent = value.length;

            if(lower){
                if(/[a-z]/.test(value)){
                    lower.classList.add("valid");
                    lower.textContent = "✔ At least 1 lowercase letter";
                } else {
                    lower.classList.remove("valid");
                    lower.textContent = "✖ At least 1 lowercase letter";
                }
            }

            if(upper){
                if(/[A-Z]/.test(value)){
                    upper.classList.add("valid");
                    upper.textContent = "✔ At least 1 uppercase letter";
                } else {
                    upper.classList.remove("valid");
                    upper.textContent = "✖ At least 1 uppercase letter";
                }
            }

            if(number){
                if(/[0-9]/.test(value)){
                    number.classList.add("valid");
                    number.textContent = "✔ At least 1 number";
                } else {
                    number.classList.remove("valid");
                    number.textContent = "✖ At least 1 number";
                }
            }

            if(special){
                if(/[\W_]/.test(value)){
                    special.classList.add("valid");
                    special.textContent = "✔ At least 1 special character";
                } else {
                    special.classList.remove("valid");
                    special.textContent = "✖ At least 1 special character";
                }
            }

            if(lengthRule){
                if(value.length >= 12){
                    lengthRule.classList.add("valid");
                    lengthRule.textContent = "✔ Minimum 12 characters";
                } else {
                    lengthRule.classList.remove("valid");
                    lengthRule.textContent = "✖ Minimum 12 characters";
                }
            }

        })
    }

});

// ===== ENCRYPT FUNCTION =====

function validateForm(){

    const image = document.getElementById("encodeImage").files[0];
    const message = document.getElementById("secretMessage").value;
    const password = document.getElementById("password").value;

    if(!image || !message || !password){
        alert("All fields are required.");
        return;
    }

    const strongRegex =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{12,}$/;

    if(!strongRegex.test(password)){
        alert("Password must meet all security requirements.");
        return;
    }

    const formData = new FormData();
    formData.append("image", image);
    formData.append("message", message);
    formData.append("password", password);

    fetch("http://127.0.0.1:5000/encode", {
        method: "POST",
        body: formData
    })
    .then(response => {
        if(!response.ok){
            throw new Error("Encryption failed");
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "encoded_image.png";
        document.body.appendChild(a);
        a.click();
        a.remove();

        alert("✅ Encryption successful!");
    })
    .catch(error => {
        alert("❌ Error: " + error.message);
    });
}

