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


function force_download(e) {

  // Get the current event & target element (cross-browser)
  e = e || window.event;
  const el = e.target || e.srcElement;

  // If this function has run on the element already (i.e. references a local blob),
  // use the href normally
  if (el.href.substring(0, 5) === 'blob:') {
    console.info('Downloading file...')
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

      // Re-click the element, now that the href is updated
      el.click();
    })
}
