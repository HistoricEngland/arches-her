define([
    'knockout',
    'viewmodels/workflow',
    'viewmodels/workflow-step',
    'views/components/workflows/new-tile-step',
    'views/components/workflows/set-tile-value',
    'views/components/workflows/get-tile-value',
    'views/components/workflows/select-resource-step'
], function(ko, Workflow, Step) {
    return ko.components.register('communication-workflow', {
        viewModel: function(params) {
            var self = this;
            params.steps = [
                {
                    title: 'Related Consultation / Date',
                    name: 'relatedconsultation',
                    description: '',
                    component: 'views/components/workflows/select-resource-step',
                    componentname: 'select-resource-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: "caf5bff9-a3d7-11e9-a2e7-00224800b26d", // Comm Date
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-tag',
                    nameheading: 'Communication',
                    namelabel: '[no label]'
                },
                {
                    title: 'Communication Details',
                    description: 'Type of Communication',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bff4-a3d7-11e9-99c5-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-tag'
                },
                {
                    title: 'Communication Details',
                    description: 'Dates of Communication',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bff9-a3d7-11e9-a2e7-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-tag'
                },
                {
                    title: 'Communication Details',
                    description: 'Subject of Communication',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bff6-a3d7-11e9-96e5-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-tag'
                },
                {
                    title: 'Attendees',
                    name: 'setname',
                    description: 'Attendee List',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bffa-a3d7-11e9-8b1b-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-user-plus'
                },
                {
                    title: 'Notes',
                    description: ' Meeting notes',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bffb-a3d7-11e9-aebc-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-lightbulb-o'
                },
                {
                    title: 'Follow-On Actions',
                    description: 'Follow-on actions, To-Dos',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bff8-a3d7-11e9-a37c-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-clipboard'
                },
                {
                    title: 'Upload Documents',
                    description: 'Document Upload',
                    component: 'views/components/workflows/new-tile-step',
                    componentname: 'new-tile-step',
                    graphid: '8d41e49e-a250-11e9-9eab-00224800b26d',
                    nodegroupid: 'caf5bff7-a3d7-11e9-baa0-00224800b26d',
                    resourceid: null,
                    tileid: null,
                    parenttileid: null,
                    icon: 'fa-file-o'
                }
            ];

            Workflow.apply(this, [params]);

            self.activeStep.subscribe(this.updateState);

            self.ready(true);
        },
        template: { require: 'text!templates/views/components/plugins/communication-workflow.htm' }
    });
});
