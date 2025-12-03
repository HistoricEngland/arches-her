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
                            let this_rid = response.related_resources.resource_instance.resourceinstanceid;
                            //need to look at the resource_relationships and find other resources that are pointing TO this one
                            other_resource_ids = [];
                            for(const rr of response.related_resources.resource_relationships){
                                if(rr.resourceinstanceidto == self.resourceinstanceid){
                                    other_resource_ids.push(rr.resourceinstanceidfrom)
                            }
                            }
                            // we now have the resources that point at this one.
                            var response_related_resources = response.related_resources.related_resources.filter((x) => other_resource_ids.includes(x.resourceinstanceid));
                            self.relations.removeAll()
                            for(r in response_related_resources){
                                var response_related_resource = response_related_resources[r]
                                if (
                                    self.graphs_list.length === 0 ||
                                    self.graphs_list.includes(response_related_resource["graph_id"])
                                ) {
                                    var graph_obj = self.graphs.find((gr) => gr.graphid === response_related_resource["graph_id"]);
                                    var graph_name = graph_obj ? graph_obj.name : "unknown";
                                    self.relations.push({"related_resource_name": response_related_resource["displayname"], "related_resource_link": arches.urls.resource_report + response_related_resource["resourceinstanceid"], "related_resource_type": graph_name})
                                }
                            }
                            return
                        })
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