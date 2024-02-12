define([
  'jquery',
  '../utils'
], function ($, Utils) {
  function A11ySingle (decorated, $element, options) {
    decorated.call(this, $element, options);
  }

  A11ySingle.prototype.bind = function (decorated, data) {

    // If orginal select had aria-describedby, add to select2-selection
    if (this.$element.attr('aria-describedby') !== undefined) {
      this.$selection
        .attr('aria-describedby', this.$element.attr('aria-describedby'));
    }

    return decorated.call(this, data);
  };

  return A11ySingle;
});
