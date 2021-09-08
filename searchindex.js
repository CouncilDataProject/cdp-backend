Search.setIndex({docnames:["cdp_backend","cdp_backend.bin","cdp_backend.database","cdp_backend.file_store","cdp_backend.infrastructure","cdp_backend.pipeline","cdp_backend.sr_models","cdp_backend.utils","cdp_backend.utils.resources","contributing","database_schema","event_gather_pipeline","index","ingestion_models","installation","modules","transcript_model"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["cdp_backend.rst","cdp_backend.bin.rst","cdp_backend.database.rst","cdp_backend.file_store.rst","cdp_backend.infrastructure.rst","cdp_backend.pipeline.rst","cdp_backend.sr_models.rst","cdp_backend.utils.rst","cdp_backend.utils.resources.rst","contributing.rst","database_schema.md","event_gather_pipeline.md","index.rst","ingestion_models.md","installation.rst","modules.rst","transcript_model.md"],objects:{"":{cdp_backend:[0,0,0,"-"]},"cdp_backend.bin":{clean_cdp_database:[1,0,0,"-"],clean_cdp_filestore:[1,0,0,"-"],create_cdp_database_uml:[1,0,0,"-"],create_cdp_event_gather_flow_viz:[1,0,0,"-"],create_cdp_ingestion_models_doc:[1,0,0,"-"],create_cdp_transcript_model_doc:[1,0,0,"-"],process_local_file:[1,0,0,"-"],run_cdp_event_gather:[1,0,0,"-"],run_cdp_event_index:[1,0,0,"-"],search_cdp_events:[1,0,0,"-"]},"cdp_backend.bin.clean_cdp_database":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.clean_cdp_filestore":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.create_cdp_database_uml":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.create_cdp_event_gather_flow_viz":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.create_cdp_ingestion_models_doc":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.create_cdp_transcript_model_doc":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.process_local_file":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.run_cdp_event_gather":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.run_cdp_event_index":{Args:[1,1,1,""],main:[1,2,1,""]},"cdp_backend.bin.search_cdp_events":{Args:[1,1,1,""],EventMatch:[1,1,1,""],SearchSortByField:[1,1,1,""],get_stemmed_grams_from_query:[1,2,1,""],main:[1,2,1,""],run_local_search:[1,2,1,""],run_remote_search:[1,2,1,""]},"cdp_backend.bin.search_cdp_events.EventMatch":{contained_grams:[1,3,1,""],datetime_weighted_relevance:[1,3,1,""],event_ref:[1,3,1,""],keywords:[1,3,1,""],pure_relevance:[1,3,1,""],selected_context_span:[1,3,1,""]},"cdp_backend.bin.search_cdp_events.SearchSortByField":{local_field:[1,3,1,""],name:[1,3,1,""],remote_field:[1,3,1,""]},"cdp_backend.database":{constants:[2,0,0,"-"],functions:[2,0,0,"-"],models:[2,0,0,"-"],types:[2,0,0,"-"],validators:[2,0,0,"-"]},"cdp_backend.database.constants":{EventMinutesItemDecision:[2,1,1,""],MatterStatusDecision:[2,1,1,""],Order:[2,1,1,""],VoteDecision:[2,1,1,""]},"cdp_backend.database.constants.EventMinutesItemDecision":{FAILED:[2,3,1,""],PASSED:[2,3,1,""]},"cdp_backend.database.constants.MatterStatusDecision":{ADOPTED:[2,3,1,""],IN_PROGRESS:[2,3,1,""],REJECTED:[2,3,1,""]},"cdp_backend.database.constants.Order":{ASCENDING:[2,3,1,""],DESCENDING:[2,3,1,""]},"cdp_backend.database.constants.VoteDecision":{ABSENT_APPROVE:[2,3,1,""],ABSENT_NON_VOTING:[2,3,1,""],ABSENT_REJECT:[2,3,1,""],ABSTAIN_APPROVE:[2,3,1,""],ABSTAIN_NON_VOTING:[2,3,1,""],ABSTAIN_REJECT:[2,3,1,""],APPROVE:[2,3,1,""],REJECT:[2,3,1,""]},"cdp_backend.database.functions":{create_body:[2,2,1,""],create_event:[2,2,1,""],create_event_minutes_item:[2,2,1,""],create_event_minutes_item_file:[2,2,1,""],create_file:[2,2,1,""],create_matter:[2,2,1,""],create_matter_file:[2,2,1,""],create_matter_sponsor:[2,2,1,""],create_matter_status:[2,2,1,""],create_minimal_event_minutes_item:[2,2,1,""],create_minimal_person:[2,2,1,""],create_minutes_item:[2,2,1,""],create_person:[2,2,1,""],create_role:[2,2,1,""],create_seat:[2,2,1,""],create_session:[2,2,1,""],create_transcript:[2,2,1,""],create_vote:[2,2,1,""],generate_and_attach_doc_hash_as_id:[2,2,1,""],get_all_of_collection:[2,2,1,""],upload_db_model:[2,2,1,""]},"cdp_backend.database.models":{Body:[2,1,1,""],Event:[2,1,1,""],EventMinutesItem:[2,1,1,""],EventMinutesItemFile:[2,1,1,""],File:[2,1,1,""],IndexedEventGram:[2,1,1,""],Matter:[2,1,1,""],MatterFile:[2,1,1,""],MatterSponsor:[2,1,1,""],MatterStatus:[2,1,1,""],MinutesItem:[2,1,1,""],Person:[2,1,1,""],Role:[2,1,1,""],Seat:[2,1,1,""],Session:[2,1,1,""],Transcript:[2,1,1,""],Vote:[2,1,1,""]},"cdp_backend.database.models.Body":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],description:[2,3,1,""],end_datetime:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],is_active:[2,3,1,""],name:[2,3,1,""],start_datetime:[2,3,1,""]},"cdp_backend.database.models.Body.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Event":{Example:[2,4,1,""],Meta:[2,1,1,""],agenda_uri:[2,3,1,""],body_ref:[2,3,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],event_datetime:[2,3,1,""],external_source_id:[2,3,1,""],hover_thumbnail_ref:[2,3,1,""],id:[2,3,1,""],minutes_uri:[2,3,1,""],static_thumbnail_ref:[2,3,1,""]},"cdp_backend.database.models.Event.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.EventMinutesItem":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],decision:[2,3,1,""],event_ref:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],index:[2,3,1,""],minutes_item_ref:[2,3,1,""]},"cdp_backend.database.models.EventMinutesItem.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.EventMinutesItemFile":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],event_minutes_item_ref:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],name:[2,3,1,""],uri:[2,3,1,""]},"cdp_backend.database.models.EventMinutesItemFile.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.File":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],description:[2,3,1,""],id:[2,3,1,""],media_type:[2,3,1,""],name:[2,3,1,""],uri:[2,3,1,""]},"cdp_backend.database.models.File.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.IndexedEventGram":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],context_span:[2,3,1,""],datetime_weighted_value:[2,3,1,""],event_ref:[2,3,1,""],id:[2,3,1,""],stemmed_gram:[2,3,1,""],unstemmed_gram:[2,3,1,""],value:[2,3,1,""]},"cdp_backend.database.models.IndexedEventGram.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Matter":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],matter_type:[2,3,1,""],name:[2,3,1,""],title:[2,3,1,""]},"cdp_backend.database.models.Matter.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.MatterFile":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],matter_ref:[2,3,1,""],name:[2,3,1,""],uri:[2,3,1,""]},"cdp_backend.database.models.MatterFile.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.MatterSponsor":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],matter_ref:[2,3,1,""],person_ref:[2,3,1,""]},"cdp_backend.database.models.MatterSponsor.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.MatterStatus":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],event_minutes_item_ref:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],matter_ref:[2,3,1,""],status:[2,3,1,""],update_datetime:[2,3,1,""]},"cdp_backend.database.models.MatterStatus.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.MinutesItem":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],description:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],matter_ref:[2,3,1,""],name:[2,3,1,""]},"cdp_backend.database.models.MinutesItem.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Person":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],email:[2,3,1,""],external_source_id:[2,3,1,""],generate_router_string:[2,4,1,""],id:[2,3,1,""],is_active:[2,3,1,""],name:[2,3,1,""],phone:[2,3,1,""],picture_ref:[2,3,1,""],router_string:[2,3,1,""],strip_accents:[2,4,1,""],website:[2,3,1,""]},"cdp_backend.database.models.Person.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Role":{Example:[2,4,1,""],Meta:[2,1,1,""],body_ref:[2,3,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],end_datetime:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],person_ref:[2,3,1,""],seat_ref:[2,3,1,""],start_datetime:[2,3,1,""],title:[2,3,1,""]},"cdp_backend.database.models.Role.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Seat":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],electoral_area:[2,3,1,""],electoral_type:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],image_ref:[2,3,1,""],name:[2,3,1,""]},"cdp_backend.database.models.Seat.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Session":{Example:[2,4,1,""],Meta:[2,1,1,""],caption_uri:[2,3,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],event_ref:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],session_datetime:[2,3,1,""],session_index:[2,3,1,""],video_uri:[2,3,1,""]},"cdp_backend.database.models.Session.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Transcript":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],confidence:[2,3,1,""],created:[2,3,1,""],file_ref:[2,3,1,""],id:[2,3,1,""],session_ref:[2,3,1,""]},"cdp_backend.database.models.Transcript.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.models.Vote":{Example:[2,4,1,""],Meta:[2,1,1,""],collection:[2,3,1,""],collection_name:[2,3,1,""],decision:[2,3,1,""],event_minutes_item_ref:[2,3,1,""],event_ref:[2,3,1,""],external_source_id:[2,3,1,""],id:[2,3,1,""],in_majority:[2,3,1,""],matter_ref:[2,3,1,""],person_ref:[2,3,1,""]},"cdp_backend.database.models.Vote.Meta":{ignore_none_field:[2,3,1,""]},"cdp_backend.database.types":{IndexedField:[2,1,1,""],IndexedFieldSet:[2,1,1,""]},"cdp_backend.database.types.IndexedField":{name:[2,3,1,""],order:[2,3,1,""]},"cdp_backend.database.types.IndexedFieldSet":{fields:[2,3,1,""]},"cdp_backend.database.validators":{UniquenessValidation:[2,1,1,""],create_constant_value_validator:[2,2,1,""],email_is_valid:[2,2,1,""],resource_exists:[2,2,1,""],router_string_is_valid:[2,2,1,""]},"cdp_backend.database.validators.UniquenessValidation":{conflicting_models:[2,3,1,""],is_unique:[2,3,1,""]},"cdp_backend.file_store":{functions:[3,0,0,"-"]},"cdp_backend.file_store.functions":{get_file_uri:[3,2,1,""],initialize_gcs_file_system:[3,2,1,""],remove_local_file:[3,2,1,""],upload_file:[3,2,1,""]},"cdp_backend.infrastructure":{cdp_stack:[4,0,0,"-"]},"cdp_backend.infrastructure.cdp_stack":{CDPStack:[4,1,1,""]},"cdp_backend.pipeline":{event_gather_pipeline:[5,0,0,"-"],event_index_pipeline:[5,0,0,"-"],ingestion_models:[5,0,0,"-"],mock_get_events:[5,0,0,"-"],pipeline_config:[5,0,0,"-"],transcript_model:[5,0,0,"-"]},"cdp_backend.pipeline.event_gather_pipeline":{SessionProcessingResult:[5,1,1,""],create_event_gather_flow:[5,2,1,""],generate_transcript:[5,2,1,""],import_get_events_func:[5,2,1,""]},"cdp_backend.pipeline.event_gather_pipeline.SessionProcessingResult":{audio_uri:[5,3,1,""],hover_thumbnail_uri:[5,3,1,""],session:[5,3,1,""],static_thumbnail_uri:[5,3,1,""],transcript:[5,3,1,""],transcript_uri:[5,3,1,""]},"cdp_backend.pipeline.event_index_pipeline":{ContextualizedGram:[5,1,1,""],EventTranscripts:[5,1,1,""],SentenceManager:[5,1,1,""],create_event_index_pipeline:[5,2,1,""]},"cdp_backend.pipeline.event_index_pipeline.ContextualizedGram":{context_span:[5,3,1,""],event_datetime:[5,3,1,""],event_id:[5,3,1,""],event_ref:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],schema:[5,4,1,""],stemmed_gram:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],unstemmed_gram:[5,3,1,""]},"cdp_backend.pipeline.event_index_pipeline.EventTranscripts":{event:[5,3,1,""],transcripts:[5,3,1,""]},"cdp_backend.pipeline.event_index_pipeline.SentenceManager":{cleaned_text:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],n_grams:[5,3,1,""],original_details:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models":{Body:[5,1,1,""],EventIngestionModel:[5,1,1,""],EventMinutesItem:[5,1,1,""],IngestionModel:[5,1,1,""],Matter:[5,1,1,""],MinutesItem:[5,1,1,""],Person:[5,1,1,""],Role:[5,1,1,""],Seat:[5,1,1,""],Session:[5,1,1,""],SupportingFile:[5,1,1,""],Vote:[5,1,1,""]},"cdp_backend.pipeline.ingestion_models.Body":{description:[5,3,1,""],end_datetime:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],is_active:[5,3,1,""],name:[5,3,1,""],schema:[5,4,1,""],start_datetime:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models.EventIngestionModel":{agenda_uri:[5,3,1,""],body:[5,3,1,""],event_minutes_items:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],hover_thumbnail_uri:[5,3,1,""],minutes_uri:[5,3,1,""],schema:[5,4,1,""],sessions:[5,3,1,""],static_thumbnail_uri:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models.EventMinutesItem":{decision:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],index:[5,3,1,""],matter:[5,3,1,""],minutes_item:[5,3,1,""],schema:[5,4,1,""],supporting_files:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],votes:[5,3,1,""]},"cdp_backend.pipeline.ingestion_models.Matter":{external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],matter_type:[5,3,1,""],name:[5,3,1,""],result_status:[5,3,1,""],schema:[5,4,1,""],sponsors:[5,3,1,""],title:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models.MinutesItem":{description:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],name:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models.Person":{email:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],is_active:[5,3,1,""],name:[5,3,1,""],phone:[5,3,1,""],picture_uri:[5,3,1,""],roles:[5,3,1,""],router_string:[5,3,1,""],schema:[5,4,1,""],seat:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],website:[5,3,1,""]},"cdp_backend.pipeline.ingestion_models.Role":{body:[5,3,1,""],end_datetime:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],schema:[5,4,1,""],start_datetime:[5,3,1,""],title:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models.Seat":{electoral_area:[5,3,1,""],electoral_type:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],image_uri:[5,3,1,""],name:[5,3,1,""],roles:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.ingestion_models.Session":{caption_uri:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],schema:[5,4,1,""],session_datetime:[5,3,1,""],session_index:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],video_uri:[5,3,1,""]},"cdp_backend.pipeline.ingestion_models.SupportingFile":{external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],name:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],uri:[5,3,1,""]},"cdp_backend.pipeline.ingestion_models.Vote":{decision:[5,3,1,""],external_source_id:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],person:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.mock_get_events":{filled_get_events:[5,2,1,""],get_events:[5,2,1,""],many_get_events:[5,2,1,""],min_get_events:[5,2,1,""]},"cdp_backend.pipeline.pipeline_config":{EventGatherPipelineConfig:[5,1,1,""],EventIndexPipelineConfig:[5,1,1,""]},"cdp_backend.pipeline.pipeline_config.EventGatherPipelineConfig":{caption_confidence:[5,3,1,""],caption_new_speaker_turn_pattern:[5,3,1,""],default_event_gather_from_days_timedelta:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],gcs_bucket_name:[5,3,1,""],get_events_function_path:[5,3,1,""],google_credentials_file:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],validated_gcs_bucket_name:[5,5,1,""]},"cdp_backend.pipeline.pipeline_config.EventIndexPipelineConfig":{datetime_weighting_days_decay:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],gcs_bucket_name:[5,3,1,""],google_credentials_file:[5,3,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],validated_gcs_bucket_name:[5,5,1,""]},"cdp_backend.pipeline.transcript_model":{SectionAnnotation:[5,1,1,""],Sentence:[5,1,1,""],SentenceAnnotations:[5,1,1,""],Transcript:[5,1,1,""],TranscriptAnnotations:[5,1,1,""],Word:[5,1,1,""],WordAnnotations:[5,1,1,""]},"cdp_backend.pipeline.transcript_model.SectionAnnotation":{description:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],generator:[5,3,1,""],name:[5,3,1,""],schema:[5,4,1,""],start_sentence_index:[5,3,1,""],stop_sentence_index:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.transcript_model.Sentence":{annotations:[5,3,1,""],confidence:[5,3,1,""],end_time:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],index:[5,3,1,""],schema:[5,4,1,""],speaker_index:[5,3,1,""],speaker_name:[5,3,1,""],start_time:[5,3,1,""],text:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""],words:[5,3,1,""]},"cdp_backend.pipeline.transcript_model.SentenceAnnotations":{from_dict:[5,4,1,""],from_json:[5,4,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.transcript_model.Transcript":{annotations:[5,3,1,""],confidence:[5,3,1,""],created_datetime:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],generator:[5,3,1,""],schema:[5,4,1,""],sentences:[5,3,1,""],session_datetime:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.transcript_model.TranscriptAnnotations":{from_dict:[5,4,1,""],from_json:[5,4,1,""],schema:[5,4,1,""],sections:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.transcript_model.Word":{annotations:[5,3,1,""],end_time:[5,3,1,""],from_dict:[5,4,1,""],from_json:[5,4,1,""],index:[5,3,1,""],schema:[5,4,1,""],start_time:[5,3,1,""],text:[5,3,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.pipeline.transcript_model.WordAnnotations":{from_dict:[5,4,1,""],from_json:[5,4,1,""],schema:[5,4,1,""],to_dict:[5,4,1,""],to_json:[5,4,1,""]},"cdp_backend.sr_models":{google_cloud_sr_model:[6,0,0,"-"],sr_model:[6,0,0,"-"],webvtt_sr_model:[6,0,0,"-"]},"cdp_backend.sr_models.google_cloud_sr_model":{GoogleCloudSRModel:[6,1,1,""]},"cdp_backend.sr_models.google_cloud_sr_model.GoogleCloudSRModel":{transcribe:[6,4,1,""]},"cdp_backend.sr_models.sr_model":{SRModel:[6,1,1,""]},"cdp_backend.sr_models.sr_model.SRModel":{transcribe:[6,4,1,""]},"cdp_backend.sr_models.webvtt_sr_model":{SpeakerRawBlock:[6,1,1,""],WebVTTSRModel:[6,1,1,""]},"cdp_backend.sr_models.webvtt_sr_model.SpeakerRawBlock":{raw_text:[6,3,1,""],words:[6,3,1,""]},"cdp_backend.sr_models.webvtt_sr_model.WebVTTSRModel":{END_OF_SENTENCE_PATTERN:[6,3,1,""],transcribe:[6,4,1,""]},"cdp_backend.utils":{constants_utils:[7,0,0,"-"],file_utils:[7,0,0,"-"],resources:[8,0,0,"-"],string_utils:[7,0,0,"-"]},"cdp_backend.utils.constants_utils":{get_all_class_attr_values:[7,2,1,""]},"cdp_backend.utils.file_utils":{find_proper_resize_ratio:[7,2,1,""],get_hover_thumbnail:[7,2,1,""],get_media_type:[7,2,1,""],get_static_thumbnail:[7,2,1,""],hash_file_contents:[7,2,1,""],resource_copy:[7,2,1,""],split_audio:[7,2,1,""]},"cdp_backend.utils.string_utils":{clean_text:[7,2,1,""]},cdp_backend:{bin:[1,0,0,"-"],database:[2,0,0,"-"],file_store:[3,0,0,"-"],infrastructure:[4,0,0,"-"],pipeline:[5,0,0,"-"],sr_models:[6,0,0,"-"],utils:[7,0,0,"-"],version:[0,0,0,"-"]}},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","function","Python function"],"3":["py","attribute","Python attribute"],"4":["py","method","Python method"],"5":["py","property","Python property"]},objtypes:{"0":"py:module","1":"py:class","2":"py:function","3":"py:attribute","4":"py:method","5":"py:property"},terms:{"0":[5,6,13,16],"00":16,"01":16,"08t03":16,"09":16,"1":[2,5,7,13,16],"10":7,"1000":2,"10t15":16,"119858":13,"12":5,"120121":5,"16":7,"1656":13,"17":[13,16],"2":[2,5,7,16],"2013":2,"2020":13,"2021":[13,16],"243":5,"3":[2,13],"30":[5,7],"4":[1,2,13],"401b":13,"419":5,"47":[13,16],"5":[4,16],"540":7,"64kb":7,"65536":7,"6c67c2a897b0":13,"7":13,"748861":13,"748871":13,"748872":13,"789a0c9f":13,"8":13,"87":5,"9":[2,5,13,16],"907997":16,"93325":16,"95":16,"960":7,"97":6,"abstract":6,"boolean":[2,7],"byte":[5,7],"case":11,"char":5,"class":[1,2,4,5,6,7],"default":[2,4,5,6,7,11,12],"do":[6,7,11],"final":5,"float":[1,5,6,7],"function":[0,5,7,11,15],"gonz\u00e1lez":13,"import":5,"int":[1,2,5,7],"new":[1,2,5,6,9],"null":16,"public":[5,14],"return":[2,3,5,6,7,11],"short":[9,11],"static":[2,7],"true":[3,5,13],"try":13,"while":[10,11,13,16],A:[2,5,6,7,9,13],And:11,As:11,But:11,For:[2,5,10,12,13,16],If:[3,5,7,9,11,13,14],In:[2,11],It:[2,6,9],Or:14,The:[2,3,4,5,6,7,11,12,13,14],Then:9,These:11,To:[13,14],aaf5:13,abc:6,about:[5,11],absent:2,absent_approv:2,absent_non_vot:2,absent_reject:2,abstain:2,abstain_approv:2,abstain_non_vot:2,abstain_reject:2,abstent:2,access:12,account:[2,3,5,12],accuraci:5,act:5,action:9,activist:12,actual:6,add:9,addition:5,adopt:[2,13],after:[7,11],afternoon:[2,5],against:5,agenda_uri:[2,5],ago:5,alex:13,algorithm:5,align:5,all:[2,4,5,7,9,11,12,13,16],allow:13,allow_nan:5,alphabet:2,alreadi:[2,7],also:[2,5,9,11,13,16],altogeth:2,alwai:[7,9,14],amend:13,an:[2,3,5,7,11,12,13,16],anaconda:9,andrew:13,ani:[2,4,5,6,7,9,11,12],annot:[5,16],api:[5,10,11,16],appear:5,appli:5,applic:12,appreci:9,approv:[2,13],april:2,ar:[2,5,9,11,13],archiv:[5,16],arg:[1,2],argpars:1,ascend:2,aspx:2,assign:6,associ:5,attach:[5,11,13],attempt:11,attende:[2,5],attribut:[5,7],audio:[5,6,7],audio_save_path:7,audio_uri:5,auto:12,autom:11,avail:[5,13],averag:5,b:9,back:11,backend:[0,4,9,14],backfil:11,bare:13,base:[1,2,4,5,6],batch:2,batch_siz:2,becaus:11,been:[2,5],befor:12,begin:5,below:[13,16],between:[5,13],bill:[2,5,13],bin:[0,5,15],bit:9,block:5,bodi:[2,5,13],body_ref:2,bool:[2,3,5,7],both:16,br:9,branch:9,bridg:13,brief_072219_2011957v:13,brown:[5,16],brows:16,bucket:[3,4,5],budget:[2,5],buffer_s:7,bugfix:9,build:9,bump2vers:9,bytearrai:5,calcul:5,call:[4,10,16],callabl:[2,5],can:[2,4,5,9,11,13,14],caption:[5,6,11],caption_confid:5,caption_new_speaker_turn_pattern:5,caption_uri:[2,5,13],cb:[5,13],cd:9,cdp:[0,2,4,5,6,9,11,13,14,16],cdp_stack:[0,15],cdpstack:4,central:12,chair:[2,5,13],chang:[5,9],charact:[2,6,7],check:[3,9],check_circular:5,checkout:9,ci:9,citi:[2,5],citywid:[2,5],cl:7,class_attr_valu:7,classmethod:[2,5],clean:[5,7,11],clean_cdp_databas:[0,15],clean_cdp_filestor:[0,15],clean_stop_word:7,clean_text:7,cleaned_text:[5,7],clerk:13,clone:[9,14],close:[5,6,11],closedcapt:13,cloud:[2,3,4,10],collect:[2,11],collection_nam:2,com:[4,9,12,13,14],command:14,comment:5,commit:9,committe:[2,5],common:7,commun:[12,13],complex:11,componentresourc:4,comput:11,confer:[2,5],confid:[2,5,6,16],config:5,configur:5,conflicting_model:2,connect:3,constant:[0,7,15],constant_cl:2,constants_util:[0,15],construct:5,contain:2,contained_gram:1,content:[13,15],context:[5,11],context_span:[2,5],contextualizedgram:5,contribut:12,convers:6,convert:6,cookiecutt:11,copi:[7,14],core:[3,5,11],correct:5,correspond:13,could:[2,5,7],council:[2,5,11,13],council_101220_2022077v:13,council_113020_2022091:13,council_113020_2022091v:13,councildataproject:[12,14],count:2,cover_nam:7,creat:[1,2,4,5,6,9,11,12],create_bodi:2,create_cdp_database_uml:[0,15],create_cdp_event_gather_flow_viz:[0,15],create_cdp_ingestion_models_doc:[0,15],create_cdp_transcript_model_doc:[0,15],create_constant_value_valid:2,create_ev:2,create_event_gather_flow:5,create_event_index_pipelin:5,create_event_minutes_item:2,create_event_minutes_item_fil:2,create_fil:2,create_matt:2,create_matter_fil:2,create_matter_sponsor:2,create_matter_statu:2,create_minimal_event_minutes_item:2,create_minimal_person:2,create_minutes_item:2,create_person:2,create_rol:2,create_seat:2,create_sess:2,create_transcript:2,create_vot:2,created_datetim:[5,16],creation:4,credenti:[2,3,5,11],credentials_fil:[2,3,5,6],credit:9,cue:5,curl:14,current:[5,7],dai:[5,11],dask:11,daskexecutor:11,data:[2,5,11,16],databas:[0,1,4,5,12,15],dataclasses_json:5,date:9,datetim:[2,5,13],datetime_weighted_relev:1,datetime_weighted_valu:2,datetime_weighting_days_decai:5,db_model:2,dd9c:13,debat:[2,5],decis:[2,5,13],dedic:12,default_event_gather_from_days_timedelta:5,definit:[13,16],delet:3,delimin:5,denot:10,depend:[2,12],deploy:[11,12],descend:2,descript:[2,5,9,16],destin:7,detail:[5,9,10,11,16],determin:7,dev:[5,9,12],dev_releas:9,develop:[11,13],diagram:10,dict:[5,13],dictat:2,did:5,differ:[11,13],directori:7,discuss:13,disk:5,displai:13,district7_50x50:13,district:[2,5,13],doc:[2,4,10],document:[2,5,10,11,16],doe:2,doesn:6,don:[11,14],done:[9,11],dot:12,download:14,dst:7,dump:5,dump_onli:5,dure:[2,4,5,9,13],e:[2,4,5,9,11],each:[2,5,10,11,12,13],earliest:5,easi:[11,13],econom:13,edit:9,educ:13,either:14,elect:[2,5],electoral_area:[2,5],electoral_typ:[2,5],els:11,email:[2,5],email_is_valid:2,enabl:[4,16],encode_json:5,end:[5,7,13,16],end_datetim:[2,5],end_of_sentence_pattern:6,end_tim:[5,16],english:7,enough:11,ensur:12,ensure_ascii:5,entir:[4,5,11],entiti:5,environ:9,equal:7,estim:5,etc:[2,4,5],event:[1,2,5],event_datetim:[2,5],event_gather_pipelin:[0,15],event_id:5,event_index_pipelin:[0,15],event_minutes_item:[2,5,13],event_minutes_item_fil:2,event_minutes_item_ref:2,event_ref:[1,2,5],eventgatherpipelineconfig:[5,11],eventindexpipelineconfig:5,eventingestionmodel:[5,11],eventmatch:1,eventminutesitem:[2,5],eventminutesitemdecis:2,eventminutesitemfil:2,eventtranscript:5,everi:[9,11],everyon:16,ex:9,exactli:5,exampl:[2,5,13],exclud:5,exclus:5,executor:11,exist:[2,3,5,7],external_source_id:[2,5],extra:[4,7],factor:7,fail:2,fals:[2,3,5,7],featur:9,feed:6,ffmpeg:[7,9],ffmpeg_stdout_path:7,field:[2,5,10,13],file:[2,3,4,5,6,7,9,11],file_ref:2,file_stor:[0,15],file_system:3,file_uri:[3,6],file_util:[0,15],filenam:3,filepath:3,filestor:5,fill:13,filled_get_ev:5,final_ratio:7,financ:[2,5,13],find:16,find_proper_resize_ratio:7,firebas:4,fireo:2,firestor:[4,10],firestore_loc:4,firestore_v1:2,first:1,five:4,flow:[5,11],follow:11,foot:11,fork:9,format:[5,6,7,11],found:[7,9,11,13],four:[2,5,11],frame:7,from:[2,3,5,6,7,11,13],from_dict:5,from_dt:5,from_json:5,from_loc:5,frontend:16,full:[2,5,11,12,13],func:2,func_path:5,gather:[5,13],gc:[5,6],gcp:4,gcp_project:4,gcp_project_id:4,gcs_bucket_nam:5,gcsf:3,gcsfilesystem:3,gener:[2,5,11,12,16],generate_and_attach_doc_hash_as_id:2,generate_router_str:2,generate_transcript:5,get:[2,3,7],get_all_class_attr_valu:7,get_all_of_collect:2,get_ev:[5,11],get_events_funct:11,get_events_function_path:5,get_file_uri:3,get_hover_thumbnail:7,get_media_typ:7,get_static_thumbnail:7,get_stemmed_grams_from_queri:1,gh:9,gif:7,git:[9,12,14],github:[9,12,14],give:11,given:[2,3,5,9,13],goal:12,goe:9,googl:[2,3,4,5],google_cloud_sr_model:[0,15],google_credentials_fil:5,googlecloudsrmodel:6,gov:13,govern:13,gram:[2,5],granicu:13,graphviz:[9,12],greater:7,greatli:9,gs:6,gt:6,guarante:5,guid:14,ha:[2,4,5],handl:[2,9],hash:[2,5,7],hash_file_cont:7,have:[2,5,12,14],head:12,height:7,hello:16,help:9,here:[2,9],hi:16,higher:5,histor:[2,5,11],hold:12,home:2,host:4,hous:13,hover:7,hover_thumbnail_ref:2,hover_thumbnail_uri:5,how:[2,4,5,7,9,11],howev:11,html:9,http:[2,4,12,13,14],hyphen:2,i:[2,4,5,11],iana:7,id:[2,4],ignore_none_field:2,imag:[5,7,13],image_ref:2,image_uri:[5,13],immedi:11,import_get_events_func:5,in_major:[2,5],in_progress:2,includ:[2,5,9,11],inclus:5,incred:11,indent:5,index:[2,5,11,12,16],indexed_event_gram:2,indexedeventgram:2,indexedfield:2,indexedfieldset:2,indic:[5,6,7],individu:5,inf:13,infer_miss:5,inform:[2,5,12,13],infrastructur:[0,2,5,13,15],ingest:[5,11],ingestion_model:[0,2,15],ingestionmodel:[5,13],initi:[2,3,4,5,6],initialize_gcs_file_system:3,input:2,insight:2,instanc:[1,2,3,4,5,6,11,12],instead:3,integr:5,intend:7,interest:11,is_act:[2,5,13],is_requir:2,is_uniqu:2,isaac:16,iso:5,item:[2,5],jackson:[5,16],jacksongen:16,job:[2,5],journalist:12,jpg:13,json:[2,3,5],just:12,kei:[2,5,11],keyword:1,kv:5,kw:5,kwarg:[2,5,6],label:5,land:5,larg:[7,11],learn:11,legal:2,legisl:[2,5],legistar2:13,legistar:2,less:[5,7],level:[0,5],lewi:13,lib:[5,16],librari:[9,12],like:[5,11,13],limit:4,lint:9,list:[1,2,4,5,6,7,11],littl:9,load_onli:5,local:[3,5,7,9],local_field:1,local_index:1,locat:4,log:7,look:[6,11,13],lorena:13,lowercas:[2,5],m2r:9,m:[9,13],machin:7,mai:2,main:[1,14],maintain:[9,11,12],major:[9,11],make:[5,9,11,13],manag:[2,5,12],mani:[2,4,5,7],manual:5,many_get_ev:5,match:7,matter:[2,5,13],matter_fil:2,matter_ref:2,matter_sponsor:2,matter_statu:2,matter_typ:[2,5,13],matterfil:[2,5],mattersponsor:2,matterstatu:2,matterstatusdecis:2,max:4,maxfield:[5,16],mayor:[2,5],md:12,me:2,mean:2,media:[6,7,13],media_typ:2,meet:[2,5],member:[2,5,12,13],memori:5,meta:2,method:[14,16],min_get_ev:5,minimum:13,minor:9,minut:[2,5],minutes_item:[2,5,13],minutes_item_ref:2,minutes_uri:[2,5],minutesitem:[2,5],mit:12,mm:5,mock:5,mock_get_ev:[0,15],mode:9,model:[0,1,5,6,10,11,12,15],modul:[12,15],more:[5,10,11,12,13,16],morn:[2,5],mosqueda:13,mosqueda_225x225:13,most:[9,14,16],mp4:[7,13],mrsc:2,mtype:7,much:13,multipl:[2,5,11],municip:2,n:[2,5],n_gram:5,na:16,name:[1,2,3,4,5,7,13,16],namedtupl:[1,2,5,6],namespac:1,need:[11,12,16],new_turn_pattern:6,non:[2,5,13],none:[1,2,3,4,5,6,7,13],normal:[2,5],nosql:10,note:[4,5,13],noth:11,now:[5,9],num_fram:7,number:[5,7],nv:2,object:[2,5,6,11,13,16],off:[2,5],offic:[2,5],ol:14,old:5,onc:14,one:[2,7,11],onli:[2,5,11],open:[5,12],open_resourc:5,oper:5,opt:4,option:[2,3,4,5,6,7,11],order:[2,5,16],ordin:[5,13],org:[2,12,13],origin:9,original_detail:5,other:[2,4,5,9,11],otherwis:[3,5],our:[9,10,11,12,13],out:13,output:6,overal:5,overwrit:7,overwritten:13,packag:[9,12,15],page:12,parallel:4,paramet:[2,3,4,5,6,7],parametr:11,parent:5,pars:5,parse_const:5,parse_float:5,parse_int:5,part:11,partial:5,pass:[2,5,9,13],passthrough:5,patch:9,path:[2,3,5,6,7,11],pathlib:[3,6,7],pattern:5,pdf:13,pedersen:13,per:2,period:[2,5],permut:5,person:[2,5,13],person_ref:2,phone:[2,5],phrase:[5,6],pick:11,pictur:5,picture_ref:2,picture_uri:[5,13],pip:[9,12,14],pipelin:[0,2,6,12,13,15,16],pipeline_config:[0,15],pixel:7,place:7,pleas:[9,12,13,16],png:7,point:[2,5,9,11],posit:[2,5,13],possibl:[9,13],prefect:[5,11],prefer:14,prefetched_ev:5,prefix:4,prepar:11,present:[2,5],presid:13,press:[2,5],preview:5,primari:[2,13],primarili:[2,5],prior:5,process:[5,12,13,14,16],process_local_fil:[0,15],produc:[5,6,7,11],progress:2,project:[9,11],proper:7,properti:5,provid:[2,3,5,7,11,12,13],publish:9,pull:[5,9],pulumi:4,pure:5,pure_relev:1,purpos:16,push:9,py:14,pypi:9,python:[5,9,13,14],queri:1,queryabl:13,queue:5,quit:11,r:5,random:5,rank:5,rare:11,rather:[5,6],ratio:7,raw:[5,7,9],raw_text:6,re:9,read:[5,7,9],readi:9,recent:14,recognit:6,recommend:[4,9,11],refer:[2,5],referenc:[2,5],reject:[2,13],relat:[2,5,12,13],releas:[9,12],relev:[2,5],rememb:11,remind:9,remot:[2,7],remote_field:1,remov:[3,7],remove_loc:3,remove_local_fil:3,repo:[5,9,14],report:[2,5],repositori:[12,14],request:[2,9,11],requir:[2,4,10],research:[12,16],resiz:7,resolut:[2,5],resolv:9,resolved_audio_save_path:7,resourc:[0,2,4,7,11],resource_copi:7,resource_exist:2,resourceopt:4,respect:5,result:[5,11],result_statu:[5,13],role:[2,5,13],rout:5,router:2,router_str:[2,5],router_string_is_valid:2,run:[4,5,9,11,12,14],run_cdp_event_gath:[0,15],run_cdp_event_index:[0,15],run_local_search:1,run_remote_search:1,s:[2,3,5,6,7,9,13],same:[2,7],satifactori:11,save:[3,7],save_nam:3,saved_path:7,scale:13,schedul:[2,5],schema:5,schemaf:5,score:[2,5],scrape:11,script:[1,5],search:[5,12,16],search_cdp_ev:[0,5,15],searchsortbyfield:1,seat:[2,5,13],seat_ref:2,seattl:[4,13],seattlechannel:13,second:[5,7],section:[5,16],sectionannot:5,see:[2,9,10,12,13,16],seen:13,segment:5,select:7,selected_context_span:1,sens:11,sentenc:[5,16],sentenceannot:5,sentencemanag:5,separ:5,serv:12,server:[4,12],servic:[2,3,4,5,13],session:[2,5,13],session_content_hash:[5,7],session_datetim:[2,5,13,16],session_index:[2,5,13],session_ref:2,sessionprocessingresult:5,set:[2,4,5,9,13],setup:14,sha256:[2,5,7],share:2,shorten:11,should:[5,6,7],sign:2,simpl:11,simpli:[6,11],singl:[2,11,12],skipkei:5,slice:5,someth:9,sort_bi:1,sort_kei:5,sourc:[1,2,3,4,5,6,7,12],speaker:[5,6],speaker_index:[5,16],speaker_nam:[5,16],speakerrawblock:6,special:[2,5],specif:[2,5,7,11,13,16],speech:[5,6],spend:[2,5],split:7,split_audio:7,sponsor:[5,13],sr_model:[0,5,15],srmodel:6,stabl:[12,16],stack:[4,12],stai:[2,12],standard:16,start:[5,11],start_datetim:[2,5],start_sentence_index:[5,16],start_tim:[5,16],static_thumbnail_ref:2,static_thumbnail_uri:5,statu:2,status:2,stderr:7,stdout:7,stemmed_gram:[2,5],step:11,still:10,stop:[5,7],stop_sentence_index:[5,16],storag:[2,4,5,12],store:[2,3,5,7,10,11,16],store_loc:5,str:[1,2,3,4,5,6,7],string:[2,5,6],string_util:[0,15],strip_acc:2,subcommitte:[2,5],submit:[2,9],submodul:15,subpackag:15,subtract:5,success:3,suppli:[5,6],support:[2,13],supporting_fil:[2,5,13],supportingfil:[2,5],sure:9,sweet:11,system:[3,5],t:[6,11,14],tag:9,take:11,taken:2,tarbal:14,target:6,task:11,technic:[2,5],teresa:13,term:[2,5],termin:14,test:[5,9,12],text:[5,7,16],than:[5,7,11],thei:[9,12],thi:[2,4,5,6,7,9,11,12,13,14],thing:2,thousand:11,three:11,through:[9,14],thumbnail:7,ti:[2,5],tiff:9,time:[2,5,7,11],timelin:2,titl:[2,5,13],to_dict:5,to_dt:5,to_json:5,togeth:[2,5],token:5,too:7,tool:[11,12,16],top:0,topic:5,total:5,track:2,transact:2,transcrib:[5,6,11],transcript:[2,5,6,11],transcript_file_ref:2,transcript_model:[0,2,6,15],transcript_uri:5,transcriptannot:5,transform:5,transport:[2,5,13],treat:5,tupl:[2,5,7],turn:6,two:[2,5,13],ty:[2,5],type:[0,3,5,6,7,13,15],uml:10,under:5,union:[3,5,6,7],uniqu:[2,5],uniquenessvalid:2,unknown:5,unstemmed_gram:[2,5],up:[7,9,11,13,16],upcom:[2,5],updat:[2,5],update_datetim:2,upload:[2,3,5,11],upload_db_model:2,upload_fil:3,upon:3,uri:[2,3,5,6,7,11,13],url:7,us:[2,3,4,5,7,10,11,12,16],usag:5,user:16,usual:2,util:[0,10,11,12,13,15],v1:5,valid:[0,15],validated_gcs_bucket_nam:5,validator_func:2,valu:[2,5,6,7,13],version:[5,9,11,15,16],vice:13,video:[5,7,11,13],video_path:7,video_read_path:7,video_uri:[2,5,13],view:[10,11],virtualenv:9,visit:12,visual:[5,11],vote:[2,5,13],votedecis:2,vtt:[6,13],w:5,wa:[2,5,7,11],we:[11,12,13,16],web:12,websit:[2,5,9,12],webvtt:[5,6],webvtt_sr_model:[0,5,15],webvttsrmodel:[5,6],welcom:9,west2:4,west:13,what:[2,5],when:[2,4,5,9],where:[7,11],whether:[2,7],which:7,who:11,whole:[5,12],width:7,word:[5,6,7,16],wordannot:5,work:[2,5,7,9,11,12],would:[4,11],write:[2,5],writebatch:2,wrong:9,www:13,x:[2,7],you:[2,4,9,11,12,14,16],your:[9,14],your_development_typ:9,your_name_her:9,zone:5},titles:["cdp_backend package","cdp_backend.bin package","cdp_backend.database package","cdp_backend.file_store package","cdp_backend.infrastructure package","cdp_backend.pipeline package","cdp_backend.sr_models package","cdp_backend.utils package","cdp_backend.utils.resources package","Contributing","CDP Database Schema","Event Gather Pipeline","Welcome to cdp-backend\u2019s documentation!","Ingestion Models","Installation","cdp_backend","Transcript Model"],titleterms:{"function":[2,3],about:12,backend:12,bin:1,cdp:[10,12],cdp_backend:[0,1,2,3,4,5,6,7,8,15],cdp_stack:4,clean_cdp_databas:1,clean_cdp_filestor:1,configur:11,constant:2,constants_util:7,content:[0,1,2,3,4,5,6,7,8],contribut:9,council:12,create_cdp_database_uml:1,create_cdp_event_gather_flow_viz:1,create_cdp_ingestion_models_doc:1,create_cdp_transcript_model_doc:1,data:[12,13],databas:[2,10,13],deploi:9,develop:[9,12],document:[12,13],event:[11,13],event_gather_pipelin:5,event_index_pipelin:5,exampl:16,exist:13,expand:13,file_stor:3,file_util:7,fill:11,from:14,gather:11,get:9,google_cloud_sr_model:6,implement:10,indic:12,infrastructur:[4,12],ingest:13,ingestion_model:5,instal:[9,12,14],item:13,licens:12,manag:11,minim:[11,13],minut:13,mock_get_ev:5,model:[2,13,16],modul:[0,1,2,3,4,5,6,7,8],note:10,packag:[0,1,2,3,4,5,6,7,8],parallel:11,pipelin:[5,11],pipeline_config:5,process:11,process_local_fil:1,project:12,releas:14,resourc:8,run_cdp_event_gath:1,run_cdp_event_index:1,s:12,schema:10,search_cdp_ev:1,sourc:14,sr_model:6,stabl:14,start:9,string_util:7,submodul:[0,1,2,3,4,5,6,7],subpackag:[0,7],tabl:12,transcript:16,transcript_model:5,type:2,updat:13,util:[7,8],valid:2,version:0,webvtt_sr_model:6,welcom:12,workflow:11}})