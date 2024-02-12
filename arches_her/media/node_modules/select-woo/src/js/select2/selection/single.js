define([
  'jquery',
  './base',
  '../utils',
  '../keys'
], function ($, BaseSelection, Utils, KEYS) {
  function SingleSelection () {
    SingleSelection.__super__.constructor.apply(this, arguments);
  }

  Utils.Extend(SingleSelection, BaseSelection);

  SingleSelection.prototype.render = function () {
    var $selection = SingleSelection.__super__.render.call(this);

    $selection.addClass('select2-selection--single');

    $selection.html(
      '<span class="select2-selection__rendered"></span>' +
      '<span class="select2-selection__arrow" role="presentation">' +
        '<b role="presentation"></b>' +
      '</span>'
    );

    return $selection;
  };

  SingleSelection.prototype.bind = function (container, $container) {
    var self = this;

    SingleSelection.__super__.bind.apply(this, arguments);

    var id = container.id + '-container';
    var label = this.options.get('label');
    var placeholder = this.options.get('placeholder');

    this.$selection.find('.select2-selection__rendered')
      .attr('id', id)
      .attr('role', 'textbox')
      .attr('aria-readonly', 'true');

    if (placeholder) {
      // role="textbox" requires a text label
      // not needed when placeholder absent as first option is selected
      this.$selection.find('.select2-selection__rendered')
        .attr('aria-label', placeholder);

      if (label) {
        // role=combobox requires a label
        // we're adding the label and placeholder here
        // so they both get announced
        this.$selection.attr('aria-label', label + ', ' + placeholder);
      }
    }

    // If element is disabled,
    // add aria-disabled to rendered element for screen readers
    if (this.container.$element.attr('disabled')) {
      this.$selection.find('.select2-selection__rendered')
        .attr('aria-disabled', 'true');
    }

    this.$selection.attr('role', 'combobox');
    this.$selection.attr('aria-controls', id);
    this.$selection.attr('aria-owns', id);
    this.$selection.attr('aria-expanded', 'false');

    this.$selection.on('mousedown', function (evt) {
      // Only respond to left clicks
      if (evt.which !== 1) {
        return;
      }

      self.trigger('toggle', {
        originalEvent: evt
      });
    });

    this.$selection.on('focus', function (evt) {
      // User focuses on the container
    });

    this.$selection.on('keydown', function (evt) {
      // If user starts typing an alphanumeric key on the keyboard,
      // open if not opened.
      if (!container.isOpen() && evt.which >= 48 && evt.which <= 90) {
        container.open();
      }
    });

    this.$selection.on('blur', function (evt) {
      // User exits the container
    });

    container.on('open', function () {
      // When the dropdown is open, aria-expanded="true"
      self.$selection.attr('aria-expanded', 'true');
    });

    container.on('close', function () {
      // When the dropdown is open, aria-expanded="false"
      self.$selection.attr('aria-expanded', 'false');

      self.$selection.removeAttr('aria-activedescendant');
    });

    container.on('focus', function (evt) {
      if (!container.isOpen()) {
        self.$selection.trigger('focus');
      }
    });

    container.on('results:focus', function (params) {
      self.$selection.attr('aria-activedescendant', params.data._resultId);
    });

    container.on('selection:update', function (params) {
      self.update(params.data);
    });
  };

  SingleSelection.prototype.clear = function () {
    this.$selection.find('.select2-selection__rendered').empty();
  };

  SingleSelection.prototype.display = function (data, container) {
    var template = this.options.get('templateSelection');
    var escapeMarkup = this.options.get('escapeMarkup');

    return escapeMarkup(template(data, container));
  };

  SingleSelection.prototype.selectionContainer = function () {
    return $('<span></span>');
  };

  SingleSelection.prototype.update = function (data) {
    if (data.length === 0) {
      this.clear();
      return;
    }

    var selection = data[0];

    var $rendered = this.$selection.find('.select2-selection__rendered');
    var formatted = this.display(selection, $rendered);

    $rendered.empty().append(formatted);

    // Update aria-label with selected option (role="textbox" requires a label)
    $rendered.attr('aria-label', selection.title || selection.text);

    var label = this.options.get('label');
    var selectedValueText = selection.title || selection.text;
    var placeholder = this.options.get('placeholder');

    // selection has role="combobox" and therefore requires a label
    // but adding just the label results in only the label being read
    // and not the selection/placeholder (in JAWS & NVDA)
    // so we add the label and the selection/placeholder
    if (label) {
      this.$selection.attr('aria-label', label + ', ' + selectedValueText);
    } else {
      this.$selection.attr('aria-label', selectedValueText);
    }
  };

  return SingleSelection;
});
