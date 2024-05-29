// Added as a hotfix for Arches 7.5.x.  To be removed for 7.6.x onwards

require([
    'jquery',
    'underscore',
    'knockout',
    'views/base-manager',
    'views/components/resource-report-abstract'
], function($, _, ko, BaseManagerView) {
    var View = BaseManagerView.extend({
        initialize: function(options){
            BaseManagerView.prototype.initialize.call(this, options);
            
            if (location.search.indexOf('print') > 0) {
                this.viewModel.loading(true);
                setTimeout(
                    function() {
                        self.viewModel.loading(false);
                        window.print();
                    },
                    25000 // a generous timeout here to allow maps/images to load
                );
            }
        }
    });
    return new View();
});
