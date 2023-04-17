{#
  Tool name must have endpoints '.submit' and '.report' to work properly.
#}
{% macro def_submit_job(tool_name, func_name='submit_job') %}
function {{func_name}}(data, modal_id, new_tab=false) {

  return $.ajax({
    type: "POST",
    processData: false,
    contentType: false,
    dataType: 'json',
    data: data,
    url:
      {%- if session["is_admin"] %}
        "{{ url_for(tool_name + '.submit') }}" + ($('#no_cache_checkbox').prop('checked') ? "?nocache=1" : ""),
      {%- else %}
        "{{ url_for(tool_name + '.submit') }}",
      {%- endif %}
  })
    .done((result) => {
      // TODO: Display message based on cache status?

      // Results are ready to be viewed
      // TODO: Redirect modal
      if (result.ready) {
        if (new_tab) {
          window.open(`{{ url_for(tool_name + '.report', id='') }}${ result.id }`, '_blank');
        } else {
          window.location.href = `{{ url_for(tool_name + '.report', id='') }}${ result.id }`;
        }
      }

      // Results are not yet ready
      else {
        $(modal_id).modal('show');
      }
    })

    // Error - check for flashed message, and reload to show if found
    .fail((error) => {
      if (error.responseJSON) {
        const message = error.responseJSON.message;
        if (message) {
          window.location.reload();
        } else {
          console.error(error);
        }
      }
    })
}
{% endmacro %}
