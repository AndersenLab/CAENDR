function can_be_disabled(tag) {
  return ['button', 'fieldset', 'input', 'optgroup', 'option', 'select', 'textarea'].includes(tag);
}

function toggle_input(idOrEl, val) {
  const el = typeof idOrEl === 'string' ? document.getElementById(idOrEl) : idOrEl;
  if (!el) {
    console.error('Could not toggle input', idOrEl);
    return;
  }

  // If element supports 'disabled' property, set that (incl. ARIA)
  const tag = el.tagName.toLowerCase();
  if (can_be_disabled(tag)) {
    el.disabled     = !val;
    el.ariaDisabled = !val;
  }

  // If not, set its background color to mimic a disabled element
  else {
    el.style.backgroundColor = `var(--${ val ? 'enabled' : 'disabled' }-color)`;
  }
}


function fetch_json(url) {
  return new Promise((resolve, reject) => {
    fetch(url).then(res => {
      if (res.status == 200) {
        resolve(res.json());
      } else {
        reject(res);
      }
    })
  })
}


// Get form data as an object
function form_data_to_object(form_id) {
  let data = {};
  $(`#${form_id}`).serializeArray().forEach(({name, value}) => {
    data[name] = value;
  });
  return data;
}


/* Force a link to download a file
 *
 * Intercepts the initial click, fetches the URL in the href attribute as a blob,
 * points the link to the new blob, and simulates a new click.
 *
 * All future clicks are allowed to use the new blob link directly.
 */
function force_download(e) {

  // Get the current event & target element (cross-browser)
  e = e || window.event;
  const el = e.target || e.srcElement;

  // If this function has run on the element already (i.e. references a local blob),
  // use the href normally
  if (el.href.substring(0, 5) === 'blob:') {
    console.warn('Downloading file again...')
    return;
  }

  // Otherwise, stop the first click from following the link
  e.preventDefault();

  // Fetch the provided URL and create a blob object from it
  fetch(el.href)
    .then(response => response.blob())
    .then(blob => {

      // Create an object URL for the blob object
      const url = URL.createObjectURL(blob);

      // Point the element's href to the URL of the new blob object
      el.href = url;

      // Create a new anchor element to download the URL
      // Do this instead of clicking the existing el directly to prevent any
      // possible recursion bugs, which could spam / timeout the browser.
      // If everything succeeds, all future clicks will use the modified href
      // in the existing anchor element. If something fails, all clicks should
      // restart the blob download process, which is is acceptable.
      const a = document.createElement('a');
      a.href = el.href;
      a.download = el.download || 'download';
      a.click();
    })
}
