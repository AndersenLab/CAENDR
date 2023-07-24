// Tracks
let tracks   = new Set();
let trackset = {};

function set_trackset(val) {
  trackset = val;
}


// Strain track templates
let templates = {};

function set_templates(val) {
  templates = val;
}


// Ensure the browser exists & is set to the desired parameters
// Returns as a Promise:
//  - browser: The browser object, after all updates are done
//  - created: True if the browser was created in this call, False if not
//  - changed: True if the browser configurations were changed in this call, False if not
//             (always True if created is True)
function create_or_update_browser(browser_div, browser_options, species) {

  const reference = {
    "id":       species['name'],
    "name":     species['short_name'],
    "fastaURL": replace_tokens("{{ fasta_url }}"),
  }

  const browser = igv.getBrowser();

  // If browser exists, swap out species params (name and FASTA file)
  if (browser) {

    // Updating the browser clears the list of tracks
    clear_tracks();

    // Load the new reference genome
    return browser.loadGenome(reference).then(() => {
      return {browser, created: false, changed: true };
    });
  }

  // If not, create a new browser
  else {

    // Set initial config options for browser
    // Merge with options provided by function call
    const options = {
      showNavigation: true,
      showKaryo: false,
      reference: reference,
      tracks: [],
      ...browser_options,
    };

    return igv.createBrowser(browser_div, options).then((browser) => {
      return { browser, created: true, changed: true };
    });
  }
}



// Add a single track to the browser by name
function add_track(track_name, track_data = null) {
  if (!tracks.has(track_name)) {
    const track = track_data || get_track(track_name)
    tracks.add(track_name);
    return igv.getBrowser().loadTrack(track).catch(error => {
      console.log('Error loading track ' + track_name + ': ', error)
    });
  }
}

// Remove a single track from the browser by name
function remove_track(track_name) {
  if (track_name == '') return;
  tracks.delete(track_name);
  return igv.getBrowser().removeTrackByName(track_name);
}

function update_track(track_name, track_data = null) {
  remove_track(track_name);
  add_track(track_name, track_data);
}

function clear_tracks() {
  clear_tracks_except([])
}

// Clear all tracks from the browser, except those specified in `track_names`
function clear_tracks_except(track_names) {

  tracks.forEach(track => {
    if (!track_names.includes(track)) {
      remove_track(track);
    }
  });
}



// Construct a track from a template
function get_track(track_name) {

  let track;

  // Retrieve or generate the track
  // If track is in default set, use it
  if (track_name in trackset) {
    track = JSON.parse( trackset[track_name] );
  }

  // If not, generate the track from a template
  else {
    if (track_name.endsWith('bam')) {
      track = fill_track_template('bam', track_name.substring(0, track_name.length - 4));
    } else {
      track = fill_track_template('vcf', track_name);
    }
  }

  // Get track params
  let params = track.params;

  // Create the full URL and replace all tokens
  params.url = replace_tokens( params.url );

  // If an index URL is defined, replace all tokens
  if (params.indexURL) {
    params.indexURL = replace_tokens( params.indexURL );
  }

  return params;
}



function fill_track_template(template_name, strain_name) {
  let template = JSON.parse( templates[template_name] );

  // Fill in strain names in top level string fields
  for (let key in template) {
    if (typeof template[key] == "string") {
      template[key] = template[key].replaceAll("${STRAIN}", strain_name);
    }
  }

  // Fill in strain name in params
  for (let key in template['params']) {
    if (typeof template['params'][key] == "string") {
      template['params'][key] = template['params'][key].replaceAll("${STRAIN}", strain_name);
    }
  }

  return template;
}
