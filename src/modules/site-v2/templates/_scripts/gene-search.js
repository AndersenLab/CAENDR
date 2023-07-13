/* Hide the gene search table, and show the loading icon if a search term has been entered.
 *
 * Arguments:
 *   - gene: The gene search term
 *   - div_ids: A dict containing IDs of elements used to display the search results:
 *     - table: The ID of the table element where results are stored. Required.
 *     - loading (optional): The ID of the table loading icon. Displays while gene search is running.
 *     - empty (optional): The ID of the empty message. Displays if no results are found.
 *     - error (optional): The ID of the error message. Displays if the server returns an error code.
 */
function prep_gene_search(gene, div_ids) {

  // Make sure table ID is provided
  if (!div_ids.table) throw Error('Must provide table ID.');

  // Get all relevant divs
  const table_div = $(div_ids.table);
  const load_div  = div_ids.loading ? $(div_ids.loading) : null;
  const empty_div = div_ids.empty   ? $(div_ids.empty)   : null;
  const error_div = div_ids.error   ? $(div_ids.error)   : null;

  // If gene is empty, hide all search elements
  if (gene.trim().length == 0) {
    swap_fade([ table_div, load_div, empty_div, error_div ])
  }

  // If gene not empty, replace the table with the loading icon
  else {
    swap_fade([ table_div, empty_div, error_div ], load_div);
  }
}


/* Query the db for genes and display in a results table.
 *
 * Arguments:
 *   - gene: The gene to query for
 *   - species: The species to query for
 *   - div_ids: A dict containing IDs of elements used to display the search results:
 *     - table: The ID of the table element to store the results in. Clears & appends rows to the tbody(s) of this table.
 *              NOTE: If used on a table with multiple tbody elements, will append to ALL bodies.
 *     - loading (optional): The ID of the table loading icon. Displays while gene search is running.
 *     - empty (optional): The ID of the empty message. Displays if no results are found.
 *     - error (optional): The ID of the error message. Displays if the server returns an error code.
 *   - callback: A function to run on each returned gene:
 *       Arguments: element index & element (gene object)
 *       Return: a list of object to be placed in table cells, or null if this gene should be skipped.
 */
function run_gene_search(gene, species, div_ids, callback) {

  if (!div_ids.table) throw Error('Must provide table ID.');

  // Make sure all whitespace is trimmed
  gene = gene.trim();

  // Get the body of the table to fill out
  const tbody = $(`${div_ids.table} > tbody`);

  // Get relevant divs
  const table_div = $(div_ids.table);
  const load_div  = div_ids.loading ? $(div_ids.loading) : null;
  const empty_div = div_ids.empty   ? $(div_ids.empty)   : null;
  const error_div = div_ids.error   ? $(div_ids.error)   : null;

  // If no search term provided, hide both dropdown elements
  if (gene.length == 0) {
    swap_fade([ table_div, load_div ])
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
      swap_fade([ load_div ]);
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
      swap_fade([ load_div ], table_div)
    }

    // If no results found, inform the user
    else {
      swap_fade([ load_div ], empty_div)
    }
  })
  .fail(function() {

    // If query returned an error, inform the user
    console.error('Gene query failed.');
    swap_fade([ load_div ], error_div);
  });
}


function format_locus_string(chrom, start, end) {
  return `${ chrom }:${ start }-${ end }`;
}


async function swap_fade(from, to = null) {

  // Filter out nulls, then wait for all elements to fade out
  await Promise.all(
    from.filter( p => p !== null ).map( el => el.fadeOut().promise() )
  );

  // If provided, fade in the target element
  if (to) to.fadeIn();
}
