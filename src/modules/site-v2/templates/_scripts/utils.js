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

  // If no href provided, print an error message
  if (!el.href) {
    console.error('No URL provided for download.')
    return;
  }

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


/* Create a DOM node from a string of HTML, without adding the element to the DOM yet */
function create_node(html) {
  const placeholder = document.createElement("div");
  placeholder.innerHTML = html;
  return placeholder.firstElementChild;
}


/* Flash a message to the user without reloading the page.
 * This function is roundabout to prevent code injection.
 */
function flash_message(message, full_msg_link=null, full_msg_body=null) {

  // Define the template for an alert popup using a static string
  {%- with msg='', category='danger' %}
  const raw_html = `{% include '_includes/alert.html' %}`;
  {%- endwith %}

  // Create as a new DOM node, and insert the desired message as text
  // Inserting as text protects against code injection
  const node = create_node(raw_html);
  node.firstElementChild.innerText = message;

  // If both full message fields are provided, add as a link & collapse dropdown
  if (full_msg_link && full_msg_body) {
    node.firstElementChild.innerText += ' ';

    // Create a unique ID to link the trigger & collapse elements
    const id = `error-dropdown-${(new Date()).getTime()}`;

    // Create a link to open the full message
    const full_msg_link_el = create_node(`<a data-bs-toggle="collapse" href="#${id}" role="button" aria-expanded="false" aria-controls="${id}"></a>`);
    full_msg_link_el.innerText = full_msg_link;
    node.firstElementChild.appendChild(full_msg_link_el);

    // Create a collapse element containing the full message
    const full_msg_body_el = create_node(`<div class="collapse" id="${id}"></div>`);
    full_msg_body_el.innerText = full_msg_body;
    node.appendChild(full_msg_body_el);
  }

  // Add the new node to the container for alert messages
  document.getElementById('alert-container').appendChild(node);

  // Italicize species name(s) in the alert message
  {%- if species_list %}
  {%- for species in species_list.values() %}
  node.innerHTML = node.innerHTML.replace('{{ species.short_name }}', '<i>{{ species.short_name }}</i>')
  {%- endfor %}
  {%- endif %}
}
