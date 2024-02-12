module('Selection containers - Single');

var SingleSelection = require('select2/selection/single');

var $ = require('jquery');
var Options = require('select2/options');
var Utils = require('select2/utils');

var options = new Options({});

test('display uses templateSelection', function (assert) {
  var called = false;

  var templateOptions = new Options({
    templateSelection: function (data) {
      called = true;

      return data.text;
    }
  });

  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    templateOptions
  );

  var out = selection.display({
    text: 'test'
  });

  assert.ok(called);

  assert.equal(out, 'test');
});

test('templateSelection can addClass', function (assert) {
  var called = false;

  var templateOptions = new Options({
    templateSelection: function (data, container) {
      called = true;
      container.addClass('testclass');
      return data.text;
    }
  });

  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    templateOptions
  );

  var $container = selection.selectionContainer();

  var out = selection.display({
    text: 'test'
  }, $container);

  assert.ok(called);

  assert.equal(out, 'test');

  assert.ok($container.hasClass('testclass'));
});

test('empty update clears the selection', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();
  var $rendered = $selection.find('.select2-selection__rendered');

  $rendered.text('testing');

  selection.update([]);

  assert.equal($rendered.text(), '');
});

test('update renders the data text', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();
  var $rendered = $selection.find('.select2-selection__rendered');

  selection.update([{
    text: 'test'
  }]);

  assert.equal($rendered.text(), 'test');
});

test('escapeMarkup is being used', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();
  var $rendered = $selection.find('.select2-selection__rendered');

  var unescapedText = '<script>bad("stuff");</script>';

  selection.update([{
    text: unescapedText
  }]);

  assert.equal(
    $rendered.text(),
    unescapedText,
    'The text should be escaped by default to prevent injection'
  );
});

test('aria-label should include placeholder and label', function (assert) {
  var options = new Options({'label': 'Example', 'placeholder': 'Choose'});
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $('#qunit-fixture .single');
  selection.bind(container, $('<span></span>'));

  assert.equal($selection.attr('aria-label'),
    'Example, Choose',
    'The container aria-label should include the label and placeholder'
  );
});

test('aria-role should be set', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $('#qunit-fixture .single');
  selection.bind(container, $('<span></span>'));

  assert.equal($selection.attr('role'),
    'combobox',
    'The container should identify as a combobox'
  );
});

test('aria-controls should be set', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $('#qunit-fixture .single');
  selection.bind(container, $('<span></span>'));

  var $rendered = $selection.find('.select2-selection__rendered');

  assert.equal(
    $selection.attr('aria-controls'),
    $rendered.attr('id'),
    'The rendered selection should control the container'
  );
});

test('aria-owns should be set', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $('#qunit-fixture .single');
  selection.bind(container, $('<span></span>'));

  var $rendered = $selection.find('.select2-selection__rendered');

  assert.equal(
    $selection.attr('aria-owns'),
    $rendered.attr('id'),
    'The rendered selection should own the container'
  );
});

test('aria-expanded should be set', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $('#qunit-fixture .single');
  selection.bind(container, $('<span></span>'));

  assert.equal(
    $selection.attr('aria-expanded'),
    'false',
    'The selection should not be expanded when it is closed'
  );

  container.trigger('open');

  assert.equal(
    $selection.attr('aria-expanded'),
    'true',
    'The selection should signal it is expanded'
  );

  container.trigger('close');

  assert.equal(
    $selection.attr('aria-expanded'),
    'false',
    'The selection should not be expanded when it is closed'
  );
});

test('aria-activedescendant should be set', function (assert) {
  var selection = new SingleSelection(
    $('#qunit-fixture .single'),
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $('#qunit-fixture .single');
  selection.bind(container, $('<span></span>'));

  container.trigger('results:focus', {
    data: {
      _resultId: '123'
    }
  });

  assert.equal(
    $selection.attr('aria-activedescendant'),
    '123',
    'activedescendant should be set'
  );

  container.trigger('close');

  assert.equal(
    $selection.attr('aria-activedescendant'),
    undefined,
    'activedescendant should not be present'
  );


});

test('update renders the aria-label with label + selection', function (assert) {
  var $element = $('#qunit-fixture .single');
  var options = new Options({'label': 'Example'});

  var selection = new SingleSelection(
    $element,
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $element;
  selection.bind(container, $('<span></span>'));

  selection.update([{
    text: 'test'
  }]);

  assert.equal($selection.attr('aria-label'),
    'Example, test',
    'The container aria-label should include the label and selection'
  );
});

test('update renders the aria-label with selection', function (assert) {
  var $element = $('#qunit-fixture .single');

  var selection = new SingleSelection(
    $element,
    options
  );

  var $selection = selection.render();

  var container = new MockContainer();
  container.$element = $element;
  selection.bind(container, $('<span></span>'));

  selection.update([{
    text: 'test'
  }]);

  assert.equal($selection.attr('aria-label'),
    'test',
    'The container aria-label should include the selection'
  );
});
