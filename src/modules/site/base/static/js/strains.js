function update_row_striping(table_selector, visible_only=true) {

  // Get all strain container elements (rows) in the given table, optionally filtering to only visible rows
  // Table data often initialized while the table itself is hidden, so getting all containers is useful
  // for initializing in that case
  const selector = `${ table_selector } .strain-entry-container` + (visible_only ? ':visible' : '');

  $(selector).each(function (index) {
    $(this).toggleClass("table-striped-row", !!(index & 1));
  });
}


function filter_strains(table_selector, species_id='', search_terms=[]) {

  // Hide all strains
  $(`${ table_selector } .strain-entry-container`).hide();

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
        $(`${ table_selector } .strain-entry-container-${ species_id }`).filter(function() {
          return rex.test($(this).children(":first").text());
        }).show();
      })
    }

    // Otherwise, show all strains matching given species
    else {
      $(`${ table_selector } .strain-entry-container-${ species_id }`).show();
    }
  }

  // Fix the striping pattern of the rows
  // If no search terms are provided, resets to original striping pattern (ignores whether rows are hidden)
  // since with no filters, no rows will be hidden
  // Useful for resetting the pattern if the entire table is hidden
  update_row_striping(table_selector, search_terms.length > 0);
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
