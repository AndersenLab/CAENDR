// Open and Close Fullscreen Buttons
const closeButton = document.getElementById("closeButton");
const fullscreenButton = document.getElementById("fullscreenButton");
const fullScreenAvailable = document.fullscreenEnabled || 
                            document.mozFullscreenEnabled ||
                            document.webkitFullscreenEnabled ||
                            document.msFullscreenEnabled


/* Run any time fullscreen changes */
function onFullscreenChange() {

  // Update the fullscreen close button
  closeButton.style.display = (closeButton.style.display === 'block') ? 'none' : 'block';

  // Check for an IGV variable and trigger browser(s) to resize
  if (typeof igv !== 'undefined') igv.visibilityChange();

  // Dispatch a unified event, so individual pages can make specific changes
  window.dispatchEvent(new CustomEvent('fullscreenchangefinished'))
}


if (fullScreenAvailable) {
  function openFullscreen() {
    if (fullscreenBrowser.requestFullscreen) {
      fullscreenBrowser.requestFullscreen();
    } else if (fullscreenBrowser.webkitRequestFullscreen) { /* Safari */
      fullscreenBrowser.webkitRequestFullscreen();
    } else if (fullscreenBrowser.msRequestFullscreen) { /* IE11 */
      fullscreenBrowser.msRequestFullscreen();
    }
  }
} else {
  // fullscreen not supported
  fullscreenButton.classList.add("d-none");
}

  function closeFullscreen() {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.webkitExitFullscreen) { /* Safari */
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) { /* IE11 */
      document.msExitFullscreen();
    }
  }

// Attach the listener to change events so it's triggered when exiting fullscreen w Esc button
document.addEventListener("fullscreenchange",    onFullscreenChange);
document.addEventListener("mozfullscreenchange", onFullscreenChange);
document.addEventListener("msfullscreenchange",  onFullscreenChange);

// Additional behavior for webkit browsers
document.addEventListener("webkitfullscreenchange", function() {
  onFullscreenChange();
  if (window.matchMedia("(min-width: 1370px)").matches) {
    closeButton.classList.display = "none";
  }
});