from Acquisition import aq_inner

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import ISiteRoot

from plone.app.upgrade.tests.base import MigrationTest

import alphas
from plone.registry.interfaces import IRegistry
from zope.component import getAdapter
from zope.component import queryUtility
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

from plone.app.controlpanel.interfaces import IEditingSchema
from plone.app.controlpanel.interfaces import IFilterTagsSchema
from plone.app.controlpanel.interfaces import ILanguageSchema
from plone.app.controlpanel.interfaces import IMailSchema
from plone.app.controlpanel.interfaces import IMarkupSchema
from plone.app.controlpanel.interfaces import INavigationSchema
from plone.app.controlpanel.interfaces import ISearchSchema
from plone.app.controlpanel.interfaces import ISecuritySchema
from plone.app.controlpanel.interfaces import ISiteSchema
from plone.app.controlpanel.interfaces import ISkinsSchema
from plone.app.controlpanel.bbb.filter import XHTML_TAGS
from Products.CMFPlone.utils import safe_unicode


class PASUpgradeTest(MigrationTest):

    def afterSetup(self):
        super(PASUpgradeTest, self).afterSetup()
        self.portal_setup = getToolByName(self.portal, 'portal_setup')
        self.portal_setup.runAllImportStepsFromProfile('profile-plone.app.controlpanel:default')

    def test_double_upgrade(self):
        # Check that calling our upgrade twice does no harm.
        alphas.lowercase_email_login(self.portal)
        alphas.lowercase_email_login(self.portal)

    def test_upgrade_with_email_login(self):
        pas = getToolByName(self.portal, 'acl_users')
        regtool = getToolByName(self.portal, 'portal_registration')
        regtool.addMember('JOE', 'somepassword')
        self.assertEqual(pas.getUserById('JOE').getUserName(), 'JOE')

        # First call.
        alphas.lowercase_email_login(self.portal)
        self.assertEqual(pas.getProperty('login_transform'), '')
        self.assertEqual(pas.getUserById('JOE').getUserName(), 'JOE')

        # If email as login is enabled, we want to use lowercase login
        # names, even when that login name is not an email address.
        ptool = getToolByName(self.portal, 'portal_properties')
        ptool.site_properties.manage_changeProperties(use_email_as_login=True)

        # Second call.
        alphas.lowercase_email_login(self.portal)
        self.assertEqual(pas.getProperty('login_transform'), 'lower')
        self.assertEqual(pas.getUserById('JOE').getUserName(), 'joe')

    def test_navigation_properties_to_registry(self):
        registry = queryUtility(IRegistry)
        registry.registerInterface(INavigationSchema)
        ttool = getToolByName(self.portal, 'portal_types')
        ptool = getToolByName(self.portal, 'portal_properties')
        siteProps = ptool['site_properties']
        navProps = ptool['navtree_properties']
        navProps.showAllParents = False
        alphas.navigation_properties_to_registry(self.portal)
        settings = registry.forInterface(INavigationSchema)
        self.assertTrue(not settings.generate_tabs == siteProps.disable_folder_sections)
        self.assertTrue(not settings.nonfolderish_tabs == siteProps.disable_nonfolderish_sections)

        allTypes = ttool.listContentTypes()
        displayed_types = tuple([
            t for t in allTypes
            if t not in navProps.metaTypesNotToList])
        for t in displayed_types:
            self.assertTrue(t in settings.displayed_types)

        self.assertEqual(settings.filter_on_workflow, navProps.enable_wf_state_filtering)
        self.assertEqual(settings.workflow_states_to_show, navProps.wf_states_to_show)
        self.assertEqual(settings.show_excluded_items, navProps.showAllParents)
        self.assertTrue(not settings.show_excluded_items)

    def test_editing_properties_to_registry(self):
        registry = queryUtility(IRegistry)
        registry.registerInterface(IEditingSchema)
        ptool = getToolByName(self.portal, 'portal_properties')
        siteProps = ptool['site_properties']
        alphas.navigation_properties_to_registry(self.portal)
        settings = registry.forInterface(IEditingSchema)

        self.assertEqual(settings.visible_ids, siteProps.visible_ids)
        self.assertEqual(settings.enable_link_integrity_checks, siteProps.enable_link_integrity_checks)
        self.assertEqual(settings.ext_editor, siteProps.ext_editor)
        self.assertEqual(settings.lock_on_ttw_edit, siteProps.lock_on_ttw_edit)

        factory = getUtility(IVocabularyFactory, 'plone.app.vocabularies.AvailableEditors')
        available_editors = factory(self.portal)
        if siteProps.default_editor in available_editors:
            self.assertEqual(settings.default_editor, siteProps.default_editor)
        else:
            self.assertTrue(settings.default_editor in available_editors)

    def test_filter_tag_properties_to_registry(self):
        registry = queryUtility(IRegistry)
        registry.registerInterface(IFilterTagsSchema)
        settings = registry.forInterface(IFilterTagsSchema)
        transform = getattr(
            getToolByName(self.portal, 'portal_transforms'), 'safe_html')
        nasty = transform.get_parameter_value('nasty_tags')
        valid = set(transform.get_parameter_value('valid_tags'))
        stripped = XHTML_TAGS - valid
        custom = valid - XHTML_TAGS
        sorted_nasty = sorted([ctype.decode('utf-8') for ctype in nasty])
        sorted_stripped = sorted([bad.decode('utf-8') for bad in stripped])
        sorted_custom = sorted([cus.decode('utf-8') for cus in custom])
        alphas.filter_tag_properties_to_registry(self.portal)
        self.assertEqual(settings.nasty_tags, sorted_nasty)
        self.assertEqual(settings.stripped_tags, sorted_stripped)
        self.assertEqual(settings.custom_tags, sorted_custom)

    def test_portal_languages_to_registry(self):

        ltool = aq_inner(getToolByName(self.portal, 'portal_languages'))
        registry = queryUtility(IRegistry)
        registry.registerInterface(ILanguageSchema)
        settings = registry.forInterface(ILanguageSchema)
        alphas.portal_languages_to_registry(self.portal)
        self.assertEqual(settings.use_combined_language_codes, ltool.use_combined_language_codes)
        factory = getUtility(IVocabularyFactory, 'plone.app.vocabularies.AvailableContentLanguages')
        available_content_languages = factory(self.portal)
        if ltool.getDefaultLanguage() in available_content_languages:
            self.assertEqual(settings.default_language, ltool.getDefaultLanguage())
        else:
            self.assertTrue(settings.default_language in available_content_languages)

    def test_markup_to_registry(self):
        pprop = getToolByName(self.portal, 'portal_properties')
        site_properties = pprop['site_properties']
        registry = queryUtility(IRegistry)
        registry.registerInterface(IMarkupSchema)
        settings = registry.forInterface(IMarkupSchema)
        markup_adapter = getAdapter(self.portal, IMarkupSchema)

        alphas.markup_properties_to_registry(self.portal)
        self.assertEqual(settings.default_type, site_properties.default_contenttype)
        self.assertEqual(settings.allowed_types, tuple(markup_adapter.allowed_types))

    def test_search_properties_to_registry(self):
        search_properties = getAdapter(self.portal, ISearchSchema)
        pprop = getToolByName(self.portal, 'portal_properties')
        name = 'plone.app.vocabularies.PortalTypes'
        util = queryUtility(IVocabularyFactory, name)
        types_voc = util(self.portal)
        registry = queryUtility(IRegistry)
        registry.registerInterface(ISearchSchema)
        settings = registry.forInterface(ISearchSchema)
        alphas.search_properties_to_registry(self.portal)
        types_not_searched = pprop['site_properties'].types_not_searched
        valid_types_not_searched = [t for t in types_not_searched if t in types_voc]
        self.assertEqual(settings.enable_livesearch, search_properties.enable_livesearch)
        self.assertEqual(settings.types_not_searched, tuple(valid_types_not_searched))

    def test_security_settings_to_registry(self):
        pprop = getToolByName(self.portal, 'portal_properties')
        site_properties = pprop['site_properties']
        mtool = getToolByName(self.portal, "portal_membership")
        security_properties = getAdapter(self.portal, ISecuritySchema)

        registry = queryUtility(IRegistry)
        registry.registerInterface(ISecuritySchema)
        settings = registry.forInterface(ISecuritySchema)

        alphas.security_settings_to_registry(self.portal)
        self.assertEqual(settings.enable_self_reg, security_properties.enable_self_reg)
        self.assertEqual(settings.enable_user_pwd_choice, not self.portal.validate_email)
        self.assertEqual(settings.enable_user_folders, mtool.memberareaCreationFlag)
        self.assertEqual(settings.allow_anon_views_about, site_properties.allowAnonymousViewAbout)
        self.assertEqual(settings.use_email_as_login, site_properties.use_email_as_login)

    def test_skins_properties_to_registry(self):
        sprops = getattr(
            getToolByName(self.portal, "portal_properties"), 'site_properties')
        skins_tool = getToolByName(self.portal, 'portal_skins')
        jstool = getToolByName(self.portal, 'portal_javascripts')
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(ISkinsSchema)

        theme = skins_tool.getDefaultSkin()
        mark_special_links = getattr(sprops, 'mark_special_links', '') == 'true' \
            and True or False
        ext_open = getattr(sprops, 'external_links_open_new_window', '') == 'true' \
            and True or False
        icon_visibility = getattr(sprops, 'icon_visibility')
        use_popups = jstool.getResource('popupforms.js').getEnabled()

        alphas.skins_properties_to_registry(self.portal)
        self.assertEqual(settings.theme, theme)
        self.assertEqual(settings.mark_special_links, mark_special_links)
        self.assertEqual(settings.ext_links_open_new_window, ext_open)
        self.assertEqual(settings.icon_visibility, icon_visibility)
        self.assertEqual(settings.use_popups, use_popups)

    def test_mail_settings_to_registry(self):
        mailhost = getToolByName(self.portal, 'MailHost')

        registry = queryUtility(IRegistry)
        registry.registerInterface(IMailSchema)
        settings = registry.forInterface(IMailSchema)
        alphas.mail_settings_to_registry(self.portal)
        self.assertEqual(settings.smtp_host, getattr(mailhost, 'smtp_host', None))
        self.assertEqual(settings.smtp_port, getattr(mailhost, 'smtp_port', None))
        self.assertEqual(settings.smtp_userid, getattr(mailhost, 'smtp_userid',
                                   getattr(mailhost, 'smtp_uid', None)))  # noqa
        self.assertEqual(settings.smtp_pass, getattr(mailhost, 'smtp_pass',
                                  getattr(mailhost, 'smtp_pwd', None)))  # noqa
        self.assertEqual(settings.email_from_name, getUtility(ISiteRoot).email_from_name)
        self.assertEqual(settings.email_from_address, getUtility(ISiteRoot).email_from_address)

    def test_site_settings_to_registry(self):
        site_properties = getattr(
            getToolByName(self.portal, "portal_properties"), 'site_properties')
        registry = queryUtility(IRegistry)
        registry.registerInterface(ISiteSchema)
        settings = registry.forInterface(ISiteSchema)

        site_title = safe_unicode(getattr(self.portal, 'title', ''))
        site_description = safe_unicode(getattr(self.portal, 'description', ''))
        exposeDCMetaTags = site_properties.exposeDCMetaTags
        enable_sitemap = site_properties.enable_sitemap
        webstats_js = safe_unicode(
            getattr(site_properties, 'webstats_js', ''))

        alphas.site_settings_to_registry(self.portal)
        self.assertEqual(settings.site_title, site_title)
        self.assertEqual(settings.site_description, site_description)
        self.assertEqual(settings.exposeDCMetaTags, exposeDCMetaTags)
        self.assertEqual(settings.enable_sitemap, enable_sitemap)
        self.assertEqual(settings.webstats_js, webstats_js)
