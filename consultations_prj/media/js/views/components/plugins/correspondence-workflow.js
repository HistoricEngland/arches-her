define([
    'knockout',
    'viewmodels/workflow',
    'viewmodels/workflow-step',
    'views/components/workflows/new-tile-step',
    'views/components/workflows/set-tile-value',
    'views/components/workflows/get-tile-value',
    'views/components/workflows/select-resource-step'
], function(ko, Workflow, Step) {
    return ko.components.register('correspondence-workflow', {
        viewModel: function(params) {
            var self = this;
            params.steps = [
                {
                    title: 'Correspondence Details',
                    description: 'New Correspondence',
                    component: 'views/components/workflows/select-resource-step',
                    componentname: 'select-resource-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: '8d41e4b4-a250-11e9-993d-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-tag'
                },
                {
                    title: 'Set Type',
                    description: 'Select Template type',
                    // component: 'views/components/workflows/file-template',
                    // componentname: 'file-template',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '97b30d4c-6c4a-11e9-853f-dca90488358a',
                    nodegroupid: '23e1ac91-6c4b-11e9-8641-dca90488358a',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-tag'
                },
                {
                    title: 'Review Letter',
                    name: 'reviewcorrespondence',
                    description: 'Review Correspondence',
                    component: 'views/components/workflows/file-template',
                    componentname: 'file-template',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: "8d41e4d1-a250-11e9-9a12-00224800b26d",
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-file-text-o'
                },
                {
                    title: 'Correspondence Workflow Complete',
                    name: 'correspondencecomplete',
                    description: '',
                    component: 'views/components/workflows/final-step',
                    componentname: 'final-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: '',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-cloud-upload',
                    nameheading: 'New Correspondence',
                    namelabel: '[no label]'
                }
            ];

            Workflow.apply(this, [params]);

            self.activeStep.subscribe(this.updateState);

            self.ready(true);
        },
        template: { require: 'text!templates/views/components/plugins/correspondence-workflow.htm' }
    });
});
