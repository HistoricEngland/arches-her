define([
    'knockout',
], function(ko) {


    GalleryViewModel = function() {
        this.selectedItem;
        this.selectItem = function(val){
            if (val && val.selected) {
                this.selectedItem = val;
                if (ko.unwrap(val) !== true) {
                    val.selected(true);
                }
            }
        }

        this.pan = ko.observable()
        this.updatePan = function(val){
            if (this.pan() !== val) {
                this.pan(val);
            } else {
                this.pan.valueHasMutated();
            }
        };
    };

    return GalleryViewModel;
});
