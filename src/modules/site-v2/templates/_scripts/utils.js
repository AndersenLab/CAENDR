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


function force_download(el, url) {

  // If this function has run on the element already, use the href normally
  if (el.href[el.href.length - 1] != '#') return;

  // Fetch the provided URL and create a blob object from it
  fetch(url)
    .then(response => response.blob())
    .then(blob => {

      // Create an object URL for the blob object
      const url = URL.createObjectURL(blob);

      // Point the element's href to the URL of the new blob object
      el.href = url;

      // Re-click the element, now that the href is updated
      el.click();
    })

  // Stop the first click from following the dummy link
  return false;
}
