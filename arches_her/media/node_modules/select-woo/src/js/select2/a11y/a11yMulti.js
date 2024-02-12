define([
  'jquery',
  '../utils'
], function ($, Utils) {
  function A11yMulti (decorated, $element, options) {
    decorated.call(this, $element, options);
  }

  A11yMulti.prototype.bind = function (decorated, container, $container) {

    // Add a container for accessible selection summary
    var selectionSummaryId = container.id + '-summary';
    this.$selectionSummary = $(
      '<span id="'+ selectionSummaryId +'" class="select2-selections"></span>'
    );
    $container.append(this.$selectionSummary);

    // If orginal select had aria-describedby, add to select2 search
    if (this.$element.attr('aria-describedby') !== undefined) {
      this.$search
        .attr('aria-describedby', this.$element.attr('aria-describedby'));
    }

    return decorated.call(this, container);
  };

  A11yMulti.prototype.update = function (decorated, data) {

    var oldAriaDescBy = this.$element.attr('aria-describedby');
    var newAriaDescBy;

    // Empty the summary of previously selected options
    this.$selectionSummary.empty();

    // Update accessible selection summary with selections
    for (var d = 0; d < data.length; d++) {
      var selection = data[d];
      var $selection = this.selectionContainer();
      var formatted = this.display(selection, $selection);

      // Update selection summary (used for aria-describedby on search input)
      if (typeof formatted === 'string') {
        this.$selectionSummary.append(formatted.trim() + ',');
      }

      if (formatted instanceof jQuery) { //jshint ignore:line
        this.$selectionSummary.append(formatted.text().trim() + ',');
      }
    }

    // Remove trailing comma if no element aria-describedby
    if (oldAriaDescBy === undefined) {
      this.$selectionSummary
        .text(this.$selectionSummary.text().replace(/,$/, ''));
    }

    // Update search field with selection summary aria-describedby
    if (oldAriaDescBy !== undefined) {
      newAriaDescBy = this.$selectionSummary.attr('id') + ' ' + oldAriaDescBy;
    } else {
      newAriaDescBy = this.$selectionSummary.attr('id');
    }
    this.$search.attr('aria-describedby', newAriaDescBy);


    return decorated.call(this, data);
  };

  return A11yMulti;
});
