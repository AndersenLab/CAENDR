{#
  Must be used before AJAX requests can run.
#}
{% macro ajax_setup(token) %}
$.ajaxSetup({
  beforeSend: function(xhr, settings) {
    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", "{{ token }}")
    }
  }
});
{% endmacro %}


{#
  Tool name must have endpoints '.submit' and '.report' to work properly.

  If defining with `as_form_data` = True, must include `ajax_setup` on the page (defined above).
#}
{% macro def_submit_job(tool_name, as_form_data=false, func_name='submit_job') %}
function {{func_name}}(data, modal_id, new_tab=false) {

  return $.ajax({
    type: "POST",
    {% if as_form_data -%} processData: false, {% endif %}
    contentType: {% if as_form_data -%} false {%- else -%} "application/json; charset=utf-8" {%- endif -%},
    dataType: 'json',
    data: {% if as_form_data -%} data {%- else -%} JSON.stringify(data) {%- endif -%},
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
