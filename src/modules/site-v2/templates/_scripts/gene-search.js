/* Hide the gene search table, and show the loading icon if a search term has been entered.
 *
 * Arguments:
 *   - gene: The gene search term
 *   - table_id: The ID of the table element where results are stored.
 *   - loading_id: The ID of the table loading icon. Displays while gene search is running.
 */
function prep_gene_search(gene, table_id, loading_id) {

  // If gene is empty, hide all search elements
  if (gene.trim().length == 0) {
    $(table_id).fadeOut();
    $(loading_id).fadeOut();
  }

  // If gene not empty, replace the table with the loading icon
  else {
    $(table_id).fadeOut().promise().done(() => { $(loading_id).fadeIn(); });
  }
}


/* Query the db for genes and display in a results table.
 *
 * Arguments:
 *   - gene: The gene to query for
 *   - species: The species to query for
 *   - table_id: The ID of the table element to store the results in. Clears & appends rows to the tbody(s) of this table.
 *       NOTE: If used on a table with multiple tbody elements, will append to ALL bodies.
 *   - loading_id: The ID of the table loading icon. Displays while gene search is running.
 *   - callback: A function to run on each returned gene:
 *       Arguments: element index & element (gene object)
 *       Return: a list of object to be placed in table cells, or null if this gene should be skipped.
 */
function run_gene_search(gene, species, table_id, loading_id, callback) {

  // Make sure all whitespace is trimmed
  gene = gene.trim();

  // Get the body of the table to fill out
  const tbody = $(`${table_id} > tbody`);

  // If no search term provided, hide both dropdown elements
  if (gene.length == 0) {
    $(table_id).fadeOut();
    $(loading_id).fadeOut();
    return;
  }

  // If search provided, clear the current table and query the database
  tbody.html("");
  $.ajax({
    url:         "{{ url_for('api_gene.api_search_genes', query='') }}" + gene + '?species=' + species.name,
    method:      "GET",
    contentType: 'application/xml',
  }).done(function(results) {

    // Map each gene to a set of cell values, and add to the table as <td> elements (if applicable)
    $.each(results, (i, row) => {
      const cell_values = callback(i, row);
      if (cell_values !== null) {
        tbody.append("<tr><td>" + cell_values.join("</td><td>") + "</td></tr>");
      }
    });

    // Hide the loading symbol & show the table
    $(loading_id).fadeOut().promise().done(() => { $(table_id).fadeIn(); });
  });
}


function format_locus_string(chrom, start, end) {
  return `${ chrom }:${ start }-${ end }`;
}
