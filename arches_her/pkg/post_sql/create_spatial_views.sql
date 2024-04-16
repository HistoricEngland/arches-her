-- Create required spatial views

DELETE FROM public.spatial_views;
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('289d89bb-47ad-40ef-89fe-3df03c265135', 'public', 'maritime', '', false, '[{"nodeid": "656c68c4-3ec0-11eb-859a-f875a44e0e11", "description": "maritime_vessel_type"}, {"nodeid": "656c41b0-3ec0-11eb-8d87-f875a44e0e11", "description": "cultural_period"}, {"nodeid": "72996eeb-3ecb-11eb-9e47-f875a44e0e11", "description": "use_phase_period"}, {"nodeid": "d00d4c8c-299f-11eb-bc0e-f875a44e0e11", "description": "name"}, {"nodeid": "ed3c32e6-29a1-11eb-82fa-f875a44e0e11", "description": "description"}, {"nodeid": "72996ee3-3ecb-11eb-ad29-f875a44e0e11", "description": "functional_craft_type"}]', false, '9f07fa25-f457-11eb-98c7-a87eeabdefba');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('440db097-a7f6-4c34-b650-14f993c8153b', 'public', 'activity', 'Used to record events relating to a particular Heritage Resource. Activities can be used to give context and meaning to the records of heritage assets. They provide information on ‘how we know what we know’ (for example investigative activities or research and analysis) or on how a particular Heritage Asset has been managed through time (management activities).', false, '[{"nodeid": "4f5eeb27-993e-11ea-b9f7-f875a44e0e11", "description": "display_date"}, {"nodeid": "be3831a5-813e-11e9-9a94-80000b44d1d9", "description": "record_status"}, {"nodeid": "2a5b99ad-fe48-11ea-84a1-f875a44e0e11", "description": "actor"}, {"nodeid": "394d15b8-8f7a-11ea-b4f5-f875a44e0e11", "description": "activity_type"}, {"nodeid": "4a7be135-9938-11ea-b0e2-f875a44e0e11", "description": "activity_name"}]', false, 'a5419248-f121-11eb-86a9-a87eeabdefba');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('eba8c62d-1c13-474d-aeba-0296559172f4', 'public', 'applicationarea', 'An area of land which is subject to a planning application and as such may have an impact on the historic environment or the setting of heritage assets.', false, '[{"nodeid": "9c9f9dc0-83bf-11ea-8d22-f875a44e0e11", "description": "application_area_name"}, {"nodeid": "48509bd3-83d4-11ea-9923-f875a44e0e11", "description": "associated_consultations"}]', false, '1909956f-3a3b-11eb-ae99-f875a44e0e11');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('2a578e84-b21a-431d-8de0-59e4d46a88fb', 'public', 'artefact', 'Defines information relating to the character of man made items of heritage significance as identified by the Portable Antiquities Scheme includes individual artefacts, architectural items, artefact assemblages, individual ecofacts and ecofact assemblages, and environmental samples.', false, '[{"nodeid": "c30977b0-991e-11ea-ba04-f875a44e0e11", "description": "description"}, {"nodeid": "dd8032af-b494-11ea-8110-f875a44e0e11", "description": "primary_reference_number"}, {"nodeid": "dd8032b1-b494-11ea-a183-f875a44e0e11", "description": "legacy_id"}, {"nodeid": "99cfe72e-381d-11e8-882c-dca90488358a", "description": "from_date"}, {"nodeid": "22e7c550-afc2-11ea-a4a8-f875a44e0e11", "description": "repository_owner"}, {"nodeid": "50edbf22-ab25-11ea-a258-f875a44e0e11", "description": "storage_area_name"}, {"nodeid": "546b1630-3ba4-11eb-9030-f875a44e0e11", "description": "artefact_type"}, {"nodeid": "5b0dfb27-7fe2-11ea-8ac9-f875a44e0e11", "description": "artefact_name"}, {"nodeid": "99cff7f8-381d-11e8-a059-dca90488358a", "description": "to_date"}, {"nodeid": "99cfffd1-381d-11e8-ab51-dca90488358a", "description": "cultural_period"}]', false, 'f7ccc8b9-f447-11eb-9cb1-a87eeabdefba');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('a9053144-4127-4519-b0e4-d5572c7c6b24', 'public', 'consultations', 'Version 0.1; A model to represent activities and information related to the review and evaluation of proposed developments or alterations to a structure.  This model supposes that an official of a government agency must review proposed construction activities and determine whether the activities require conditions/mitigations to conform with local requirements.  This model allows for formal application review and informal (e.g.: pre-application) consultations.', false, '[{"nodeid": "1b0e15ec-8864-11ea-8493-f875a44e0e11", "description": "proposal_text"}, {"nodeid": "40eff4cd-893a-11ea-b0cc-f875a44e0e11", "description": "log_date"}, {"nodeid": "4ad69684-951f-11ea-b5c3-f875a44e0e11", "description": "consultation_name"}, {"nodeid": "54de6acc-8895-11ea-9067-f875a44e0e11", "description": "application_type"}, {"nodeid": "73fdfe62-8895-11ea-a058-f875a44e0e11", "description": "development_type"}, {"nodeid": "b37552bd-9527-11ea-97f4-f875a44e0e11", "description": "primary_reference_number"}]', false, 'b949053a-184f-11eb-ac4a-f875a44e0e11');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('bdbd2722-70dd-4c2b-ad56-a0622c6acff7', 'public', 'area', 'Used to record complex human-made, or human conceived, sites, areas or landscapes.  Areas can be anything from a simple prehistoric settlement site (evidenced by a few flint-working fragments) to large-scale, urban conservation areas incorporating multiple assets within a city. The use of Area or Monument will be a question of granularity. For building complexes such as castles, prisons and airfields, Area may be used to record the footprint of the site, eg. the curtain wall and outer defences of a castle. This Area can then be used as the parent for multiple Monument records.', false, '[{"nodeid": "d17aa1e4-28cd-11eb-83b8-f875a44e0e11", "description": "shine_significance"}, {"nodeid": "8dca12b3-edeb-11eb-a9ee-a87eeabdefba", "description": "primary_reference_number"}, {"nodeid": "a4a816e6-efa9-11eb-b0de-a87eeabdefba", "description": "designation_or_protection_type"}, {"nodeid": "a4a816f0-efa9-11eb-969d-a87eeabdefba", "description": "grade"}, {"nodeid": "b334dde5-4e87-11eb-9576-f875a44e0e11", "description": "cultural_period"}, {"nodeid": "b334dde6-4e87-11eb-a67c-f875a44e0e11", "description": "asset_type"}, {"nodeid": "ed6c28c2-1861-11eb-9f92-f875a44e0e11", "description": "functional_type"}, {"nodeid": "ed6c28c3-1861-11eb-9f6e-f875a44e0e11", "description": "use_phase_period"}, {"nodeid": "f3cc1684-185b-11eb-9a07-f875a44e0e11", "description": "description"}]', false, '64be56e3-3ee5-11eb-b1f0-f875a44e0e11');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('3291b08d-a6be-4782-b4cc-b568a1418644', 'public', 'heritagestory', 'Used to record  thematic stories (usually associated with an historic event or period) which can provide more detailed background to the heritage assets, areas and artefact. The Heritage Story creates a user-friendly story which helps place the assets in their context within the historic environment.', false, '[{"nodeid": "4365828a-99e3-11ea-b6fb-f875a44e0e11", "description": "description"}, {"nodeid": "44441e0c-99ac-11ea-97cc-f875a44e0e11", "description": "primary_reference_number"}, {"nodeid": "4bc44105-99aa-11ea-aaa3-f875a44e0e11", "description": "name"}]', false, '38521798-3bd0-11eb-ad57-f875a44e0e11');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('82591001-1462-4045-923b-df8c8fa2d8f8', 'public', 'aircraft', 'Last Updated 1st May 2019', false, '[{"nodeid": "7f5591c5-efed-11eb-8e44-a87eeabdefba", "description": "primary_reference_number"}, {"nodeid": "20d7355e-28e1-11eb-bdbc-f875a44e0e11", "description": "description"}, {"nodeid": "446d5c4c-3e14-11eb-8095-f875a44e0e11", "description": "aircraft_type"}, {"nodeid": "490c26da-efe9-11eb-abc4-a87eeabdefba", "description": "name"}]', false, '9766b0d4-f450-11eb-83b6-a87eeabdefba');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('a67d179c-e16c-429d-9d8b-0fd47e2d5abb', 'public', 'historiclandscapecharacter', 'Used to record areas of the historic landscape. Historic Landscape Characterization is a method of identifying and interpreting the varying historic character within an area that looks beyond individual heritage assets as it brings together an understanding of the whole landscape and townscape.', false, '[{"nodeid": "4cf307e2-07b5-11eb-8253-f875a44e0e11", "description": "name"}, {"nodeid": "89a3e510-07b9-11eb-b1b2-f875a44e0e11", "description": "hlc_type"}, {"nodeid": "4a1e7dc7-f000-11eb-ac44-a87eeabdefba", "description": "primary_reference_number"}, {"nodeid": "3d22bf22-1aa8-11eb-a368-f875a44e0e11", "description": "description"}]', false, '6678040f-3dff-11eb-a042-f875a44e0e11');
INSERT INTO public.spatial_views (spatialviewid, schema, slug, description, ismixedgeometrytypes, attributenodes, isactive, geometrynodeid) VALUES ('27318c10-adc4-421c-9e93-9c007ceee035', 'public', 'monument', 'Used to record built works, human-made structures and human-modified features. These can range from a single post box to a palace complex. The use of Monument or Area will be a question of granularity.', false, '[{"nodeid": "77e8f28d-efdc-11eb-afe4-a87eeabdefba", "description": "construction_phase_type"}, {"nodeid": "676d47ff-9c1c-11ea-b07f-f875a44e0e11", "description": "monument_name"}, {"nodeid": "325a2f33-efe4-11eb-b0bb-a87eeabdefba", "description": "primary_reference_number"}, {"nodeid": "ba345577-b554-11ea-a9ee-f875a44e0e11", "description": "description"}, {"nodeid": "6af2a0ce-efc5-11eb-88d1-a87eeabdefba", "description": "designation_or_protection_type"}, {"nodeid": "b2133e72-efdc-11eb-a68d-a87eeabdefba", "description": "use_phase_period"}, {"nodeid": "b2133e6b-efdc-11eb-aa04-a87eeabdefba", "description": "functional_type"}, {"nodeid": "77e8f29d-efdc-11eb-b890-a87eeabdefba", "description": "cultural_period"}]', false, '87d3d7dc-f44f-11eb-bee9-a87eeabdefba');