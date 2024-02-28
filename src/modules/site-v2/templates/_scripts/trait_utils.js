// Render all provided components of the display name
function traitNameHTML(name_1, name_2, name_3) {
  let nameHTML;
  nameHTML = `<strong>${name_1}</strong>`;
  if (name_2) {
    nameHTML += `<p class="mb-0">${name_2}</p>`;
  }
  if (name_3) {
    if (!name_2) nameHTML += '<br />';
    nameHTML += `<em>${name_3}</em>`;
  }
  return nameHTML;
}


function queryTraitByName(trait_name, csrf_token=null) {

  // Construct the data object, using the optional CSRF token if provided
  let data = {trait_name};
  if (csrf_token !== null) data['csrf_token'] = csrf_token;

  // Return the AJAX request as a Promise object
  return $.ajax({
      type:        "POST",
      url:         "{{ url_for('phenotype_database.get_traits_json') }}",
      data:        JSON.stringify({trait_name}),
      contentType: "application/json",
      dataType:    "json",
  });
}