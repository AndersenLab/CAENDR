{#
  Tool name must have endpoints '.submit' and '.report' to work properly.
#}
{% macro submit_job(tool_name, form_id, modal_id) %}

  // Get form data
  var data = new FormData($("{{ form_id }}")[0]);

  // Send request
  $.ajax({
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

    // Handle results
    success: function(result) {

      // Error - Reload to show flashed message
      // TODO: Preserve species & label values across reload?
      if (!result.succeeded) {
        window.location.reload();
        return;
      }

      // TODO: Display message based on cache status?

      // Results are ready to be viewed
      // TODO: Redirect modal
      if (result.ready) {
        window.location.href = `{{ url_for(tool_name + '.report', id='') }}${ result.id }`;
      }

      // Results are not yet ready
      else {
        $("{{ modal_id }}").modal('show');
      }

      // Reset the form after a successful (non-error) submission
      resetForm();
    },

    // TODO: Error handling
    error: function(error) {
      enableButton();
    }
  });
{% endmacro %}
