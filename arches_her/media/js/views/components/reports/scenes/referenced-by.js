define([
    'underscore',
    'knockout',
    'arches',
    'utils/report',
    'bindings/datatable'
], function(_, ko, arches, reportUtils) {
    return ko.components.register('views/components/reports/scenes/referenced-by', {
        viewModel: function(params) {
            const self = this;
            Object.assign(self, reportUtils);
            self.resourceinstanceid = params.resourceInstanceId;
            self.graphs_array = params.graphs || [];
            self.graphs_list = []
            self.graphs = []
            self.relations = ko.observableArray();
            self.visible = {
                referencedBy: ko.observable(true),
            }

            // referenced by table configuration
            self.referencedByTwoColumnTableConfig = {
                ...self.defaultTableConfig,
                "paging": true,
                "searching": true,
                "scrollY": "250px",
                "columns": Array(2).fill(null),
                "bDestroy": true
            };

            self.getGraphs = function(){
                return $.ajax({
                    url: arches.urls.graphs_api,
                    context: this,
                }).done(function(graphs_response) {
                    self.graphs = ko.unwrap(graphs_response)
                    self.graphs_list = []
                    for(g in self.graphs_array){
                        var graph_find_result = self.graphs.find((gr) => gr.name === self.graphs_array[g])
                        self.graphs_list.push(graph_find_result.graphid)
                    }
                    return
                }).fail(function() {
                    // error
               })
            }


            self.getRelatedResources = function(){
                return $.ajax({
                    url: arches.urls.related_resources + self.resourceinstanceid,
                    context: self,
                })
                .done(function(response) {
                    self.getGraphs().then(function(){
                        const relationships = response.related_resources.resource_relationships;
                        const relatedResources = response.related_resources.related_resources;
                        // Collect resource IDs that point to this resource
                        const otherResourceIds = relationships
                            .filter(rr => rr.resourceinstanceidto === self.resourceinstanceid)
                            .map(rr => rr.resourceinstanceidfrom);

                        // Filter related resources that reference this one
                        const filteredResources = relatedResources.filter(x => otherResourceIds.includes(x.resourceinstanceid));

                        self.relations.removeAll();
                        filteredResources.forEach(resource => {
                            if (
                                self.graphs_list.length === 0 ||
                                self.graphs_list.includes(resource.graph_id)
                            ) {
                                const graphObj = self.graphs.find(gr => gr.graphid === resource.graph_id);
                                const graphName = graphObj ? graphObj.name : "unknown";
                                self.relations.push({
                                    related_resource_name: resource.displayname,
                                    related_resource_link: arches.urls.resource_report + resource.resourceinstanceid,
                                    related_resource_type: graphName
                                });
                            }
                        });
                    });
                })
                .fail(function() {
                    // error
                });
            };

            // Call getRelatedResources to trigger data loading on component initialization
            self.getRelatedResources();
            
        },
        template: { require: 'text!templates/views/components/reports/scenes/referenced-by.htm' }
    });
});