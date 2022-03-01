define([
    'knockout',
    'arches'
], function (ko, arches) {

    var Accessibility = function (params) {
        this.sometests = params.sometests.map(function (st) {
            return st;
        }, this);
    };

    return ko.components.register('accessibility', {
        viewModel: Accessibility,
        template: { require: 'text!templates/views/components/plugins/accessibility.htm' }
    });

});