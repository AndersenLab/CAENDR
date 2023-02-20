function filter_strains(species_id, search_terms) {

  // Hide all strains
  $('.strain-entry-container').hide();

  // If no species ID provided
  if (species_id) {

    // If search string(s) provided, show matching strains
    if (search_terms) {
      search_terms.forEach(function(r) {
        var rex = new RegExp(r, "i");
        $(`.strain-entry-container-${ species_id }`).filter(function() {
          return rex.test($(this).text());
        }).show();
      })
    }

    // Otherwise, show all strains matching given species
    else {
      $(`.strain-entry-container-${ species_id }`).show()
    }
  }
}


function update_strain_dropdown(id, strains, species, initial_value = null) {

  // Clear the specified dropdown
  $(id).empty();

  // If strains provided, fill out the dropdown
  if (strains[species['name']]) {

    // Create an option for each strain
    strains[species['name']].forEach((val) => {
      $(id).append( $("<option />").val(val).text(val) );
    });

    // If an initial default val is provided, select it
    if (initial_value) {
      $(id).val(initial_value);
    }
  }

  // If no strains found, print a warning message
  else {
    console.warn(`Couldn't find strains for species ${species['name']}`);
  }
}
