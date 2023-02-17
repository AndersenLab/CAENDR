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