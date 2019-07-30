define([
    'underscore',
    'jquery',
    'arches',
    'knockout',
    'knockout-mapping',
    'models/graph',
    'viewmodels/card',
    'viewmodels/provisional-tile',
    'viewmodels/alert'
], function(_, $, arches, ko, koMapping, GraphModel, CardViewModel, ProvisionalTileViewModel, AlertViewModel) {
    function viewModel(params) {
        var self = this;
        console.log(params);
        if (!params.resourceid() && params.requirements){
            // console.log('whats this?',params.requirements.resourceid);
            params.resourceid(params.requirements.resourceid);
            params.tileid(params.requirements.tileid);
        }
        var url = arches.urls.api_card + (ko.unwrap(params.resourceid) || ko.unwrap(params.graphid));

        // this.card = ko.observable();
        // this.tile = ko.observable();
        this.resValue = ko.observable();
        this.loading = params.loading || ko.observable(false);
        this.alert = params.alert || ko.observable(null);
        this.resourceId = params.resourceid || ko.observable();
        this.complete = params.complete || ko.observable();
        this.completeOnSave = params.completeOnSave === false ? false : true;
        this.loading(true);

        $.getJSON(url, function(data) {
            var handlers = {
                'after-update': [],
                'tile-reset': []
            };
            var displayname = ko.observable(data.displayname);
            // var createLookup = function(list, idKey) {
            //     return _.reduce(list, function(lookup, item) {
            //         lookup[item[idKey]] = item;
            //         return lookup;
            //     }, {});
            // };
            // var flattenTree = function(parents, flatList) {
            //     _.each(ko.unwrap(parents), function(parent) {
            //         flatList.push(parent);
            //         var childrenKey = parent.tiles ? 'tiles' : 'cards';
            //         flattenTree(
            //             ko.unwrap(parent[childrenKey]),
            //             flatList
            //         );
            //     });
            //     return flatList;
            // };

            self.reviewer = data.userisreviewer;
            // self.provisionalTileViewModel = new ProvisionalTileViewModel({
            //     tile: self.tile,
            //     reviewer: data.userisreviewer
            // });

            var graphModel = new GraphModel({
                data: {
                    nodes: data.nodes,
                    nodegroups: data.nodegroups,
                    edges: []
                },
                datatypes: data.datatypes
            });

            // var topCards = _.filter(data.cards, function(card) {
            //     var nodegroup = _.find(data.nodegroups, function(group) {
            //         return group.nodegroupid === card.nodegroup_id;
            //     });
            //     return !nodegroup || !nodegroup.parentnodegroup_id;
            // }).map(function(card) {
            //     params.nodegroupid = params.nodegroupid || card.nodegroup_id;
            //     return new CardViewModel({
            //         card: card,
            //         graphModel: graphModel,
            //         tile: null,
            //         resourceId: self.resourceId,
            //         displayname: displayname,
            //         handlers: handlers,
            //         cards: data.cards,
            //         tiles: data.tiles,
            //         provisionalTileViewModel: self.provisionalTileViewModel,
            //         cardwidgets: data.cardwidgets,
            //         userisreviewer: data.userisreviewer,
            //         loading: self.loading
            //     });
            // });

            // topCards.forEach(function(topCard) {
            //     topCard.topCards = topCards;
            // });

            // self.widgetLookup = createLookup(
            //     data.widgets,
            //     'widgetid'
            // );
            // self.cardComponentLookup = createLookup(
            //     data['card_components'],
            //     'componentid'
            // );
            // self.nodeLookup = createLookup(
            //     graphModel.get('nodes')(),
            //     'nodeid'
            // );
            self.on = function(eventName, handler) {
                if (handlers[eventName]) {
                    handlers[eventName].push(handler);
                }
            };

            // flattenTree(topCards, []).forEach(function(item) {
            //     if (item.constructor.name === 'CardViewModel' && item.nodegroupid === ko.unwrap(params.nodegroupid)) {
            //         if (ko.unwrap(params.parenttileid) && item.parent && ko.unwrap(params.parenttileid) !== item.parent.tileid) {
            //             return;
            //         }
            //         self.card(item);
            //         if (ko.unwrap(params.tileid)) {
            //             ko.unwrap(item.tiles).forEach(function(tile) {
            //                 if (tile.tileid === ko.unwrap(params.tileid)) {
            //                     self.tile(tile);
            //                 }
            //             });
            //         } else {
            //             self.tile(item.getNewTile());
            //         }
            //     }
            // });
            self.loading(false);
            // commented the line below because it causes steps to automatically advance on page reload
            // self.complete(!!ko.unwrap(params.tileid));
        });
        params.tile = self.tile;
        params.stateProperties = function(){
            return {
                resourceid: ko.unwrap(params.resourceid),
                tile: !!(ko.unwrap(params.tile)) ? koMapping.toJS(params.tile().data) : undefined,
                tileid: !!(ko.unwrap(params.tile)) ? ko.unwrap(params.tile().tileid): undefined
            };
        };
        

        self.saveResourceInstance = function() {
            console.log(params);
            if (self.resValue() != null) {
                console.log(self.resValue());
                params.resourceid(self.resValue());
                self.complete(true);
            }
        }

        self.onSaveSuccess = function(tiles) {
            var tile;
            if (tiles.length > 0) {
                tile = tiles[0];
                params.resourceid(tile.resourceinstance_id);
                params.tileid(tile.tileid);
                self.resourceId(tile.resourceinstance_id);
            }
            if (self.completeOnSave === true) {
                self.complete(true);
            }
        };

    }
    ko.components.register('select-resource-step', {
        viewModel: viewModel,
        template: {
            require: 'text!templates/views/components/workflows/select-resource-step.htm'
        }
    });
    return viewModel;
});
