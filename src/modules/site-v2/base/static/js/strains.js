function filter_strains(species_id='', search_terms=[]) {

  // Hide all strains
  $('.strain-entry-container').hide();

  // If no species ID provided, no strains will be shown
  if (species_id) {

    // Filter out blank search terms
    search_terms = search_terms.filter(t => t.trim())

    // If search string(s) provided, show matching strains
    // Since any matching strain is shown, acts like "OR"
    if (search_terms.length > 0) {
      search_terms.forEach(function(r) {
        var rex = new RegExp(r, "i");

        // Show all containers where the first child element (the table cell with the strain name) matches the RegEx
        $(`.strain-entry-container-${ species_id }`).filter(function() {
          return rex.test($(this).children(":first").text());
        }).show();
      })
    }

    // Otherwise, show all strains matching given species
    else {
      $(`.strain-entry-container-${ species_id }`).show()
    }
  }
}


function update_strain_dropdown(id='', strains={}, species={}, initial_value=null) {

  // Ensure dropdown element exists
  if (id === '' || !document.getElementById(id)) {
    throw new Error(`Could not find strain dropdown with id "${id}".`);
  }

  const selector = '#' + id;

  // Clear the specified dropdown
  $(selector).empty();

  // If strains provided, fill out the dropdown
  if (strains[species['name']]) {

    // Create an option for each strain
    strains[species['name']].forEach((val) => {
      $(selector).append( $("<option />").val(val).text(val) );
    });

    // If an initial default val is provided, select it
    if (initial_value !== null) {
      $(selector).val(initial_value);
    }
  }

  // If no strains found, throw an error
  else {
    throw new Error(`Couldn't find strains for species ${species['name']}`);
  }
}
