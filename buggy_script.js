// Is code mein jaan boojh kar ek ghalti hai.
// 'getElementById' ki jagah 'getElementByID' likha hai (D bara hai).
    
document.addEventListener('DOMContentLoaded', function() {
  const button = document.getElementById('testButton');
  const messageDiv = document.getElementByID('message'); // <--- YAHAN GHALTI HAI
    
  button.addEventListener('click', function() {
    messageDiv.textContent = 'Button was clicked!';
  });
});
