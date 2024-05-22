/** @odoo-module */

import tour from 'web_tour.tour';
import { openCommandBar } from '../knowledge_tour_utils.js';


tour.register('knowledge_article_command_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.$anchor[0]);
    },
}, { // click on the /article command
    trigger: '.oe-powerbox-commandName:contains("Article")',
    run: 'click',
}, { // select an article in the list
    trigger: '.select2-results > .select2-result:contains("EditorCommandsArticle")',
    run: 'click',
    in_modal: false,
}, { // wait for the choice to be registered
    trigger: '.select2-chosen:contains("EditorCommandsArticle")',
    run: () => {},
}, { // click on the "Insert Link" button
    trigger: '.modal-footer button.btn-primary',
    run: 'click'
}, { // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_article:contains("EditorCommandsArticle")',
    run: 'click',
}, { // check that the view switched to the corresponding article while keeping the breadcrumbs history
    trigger: '.o_knowledge_header:has(.o_breadcrumb_article_name_container:contains("EditorCommandsArticle")):has(.breadcrumb-item > a:contains("EditorCommandsArticle"))'
}]);
