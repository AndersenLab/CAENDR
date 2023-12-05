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
function {{func_name}}(data, modal_id, config={}) {

  // Extract configuration settings w default values
  const new_tab         = config.hasOwnProperty('new_tab')         ? config['new_tab']         : false;
  const propagate_error = config.hasOwnProperty('propagate_error') ? config['propagate_error'] : true;

  // Gather URL variable(s)
  let url_vars = [];
  if (propagate_error) {
    url_vars.push('reloadonerror=0');
  }
  {%- if session["is_admin"] %}
  if ($('#no_cache_checkbox').prop('checked')) {
    url_vars.push('nocache=1');
  }
  {%- endif %}

  // Create full URL, appending URL vars if any were created
  let url = "{{ url_for(tool_name + '.submit') }}";
  if (url_vars.length) {
    url += '?' + url_vars.join('&');
  }

  return $.ajax({
    type: "POST",
    {% if as_form_data -%} processData: false, {% endif %}
    contentType: {% if as_form_data -%} false {%- else -%} "application/json; charset=utf-8" {%- endif -%},
    dataType: 'json',
    data: {% if as_form_data -%} data {%- else -%} JSON.stringify(data) {%- endif -%},
    url: url,
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
          if (!propagate_error) window.location.reload();
        } else {
          console.error(error);
        }
      }
    })
}
{% endmacro %}
