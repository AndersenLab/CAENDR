/* Hide the gene search table, and show the loading icon if a search term has been entered.
 *
 * Arguments:
 *   - gene: The gene search term
 *   - selectors: A dict containing selectors for the elements used to display the search results:
 *     - table:              Selector for the table element where results are stored. Required.
 *     - loading (optional): Selector for the table loading icon. Displays while gene search is running.
 *     - empty (optional):   Selector the empty message. Displays if no results are found.
 *     - error (optional):   Selector the error message. Displays if the server returns an error code.
 */
function prep_gene_search(gene, selectors) {

  // Make sure table ID is provided
  if (!selectors.table) throw Error('Must provide table ID.');

  // Get all elements
  const table_el = $(selectors.table);
  const load_el  = selectors.loading ? $(selectors.loading) : null;
  const empty_el = selectors.empty   ? $(selectors.empty)   : null;
  const error_el = selectors.error   ? $(selectors.error)   : null;

  // If gene is empty, hide all search elements
  if (gene.trim().length == 0) {
    swap_fade([ table_el, load_el, empty_el, error_el ])
  }

  // If gene not empty, replace the table with the loading icon
  else {
    swap_fade([ table_el, empty_el, error_el ], load_el);
  }
}


/* Query the db for genes and display in a results table.
 *
 * Arguments:
 *   - gene: The gene to query for
 *   - species: The species to query for
 *   - selectors: A dict containing selectors for the elements used to display the search results:
 *     - table:              Selector for the table element to store the results in.
 *                           Clears & appends rows to the tbody(s) of this table.
 *                             NOTE: If used on a table with multiple tbody elements, will append to ALL bodies.
 *     - loading (optional): Selector for the table loading icon. Displays while gene search is running.
 *     - empty (optional):   Selector the empty message. Displays if no results are found.
 *     - error (optional):   Selector the error message. Displays if the server returns an error code.
 *   - callback: A function to run on each returned gene:
 *       Arguments: element index & element (gene object)
 *       Return: a list of object to be placed in table cells, or null if this gene should be skipped.
 */
function run_gene_search(gene, species, selectors, callback) {

  if (!selectors.table) throw Error('Must provide table ID.');

  // Make sure all whitespace is trimmed
  gene = gene.trim();

  // Get the body of the table to fill out
  const tbody = $(`${selectors.table} > tbody`);

  // Get all elements
  const table_el = $(selectors.table);
  const load_el  = selectors.loading ? $(selectors.loading) : null;
  const empty_el = selectors.empty   ? $(selectors.empty)   : null;
  const error_el = selectors.error   ? $(selectors.error)   : null;

  // If no search term provided, hide both dropdown elements
  if (gene.length == 0) {
    swap_fade([ table_el, load_el ])
    return;
  }

  // If search provided, clear the current table and query the database
  tbody.html("");
  return $.ajax({
    url:         "{{ url_for('api_gene.api_search_genes', query='') }}" + gene + '?species=' + species.name,
    method:      "GET",
    contentType: 'application/xml',
  })
  .done(function(results) {

    // Null results - query evaluated to empty
    if (results === null) {
      swap_fade([ load_el ]);
    }

    // If one or more results found, display to user
    else if (results.length > 0) {

      // Map each gene to a set of cell values, and add to the table as <td> elements (if applicable)
      $.each(results, (i, row) => {
        const cell_values = callback(i, row);
        if (cell_values !== null) {
          tbody.append("<tr><td>" + cell_values.join("</td><td>") + "</td></tr>");
        }
      });

      // Hide the loading symbol & show the table
      swap_fade([ load_el ], table_el)
    }

    // If no results found, inform the user
    else {
      swap_fade([ load_el ], empty_el)
    }
  })
  .fail(function() {

    // If query returned an error, inform the user
    console.error('Gene query failed.');
    swap_fade([ load_el ], error_el);
  });
}


function format_locus_string(chrom, start, end) {
  return `${ chrom }:${ start }-${ end }`;
}


async function swap_fade(from, to = null) {

  // Filter out nulls, then wait for all elements to fade out
  await Promise.all(
    from.filter( el => el !== null ).map( el => el.fadeOut().promise() )
  );

  // If provided, fade in the target element
  if (to) to.fadeIn();
}
