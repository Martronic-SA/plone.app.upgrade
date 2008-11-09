from Products.CMFCore.utils import getToolByName

from plone.app.upgrade.utils import logger
from plone.app.upgrade.utils import loadMigrationProfile


_KNOWN_ACTION_ICONS = {
    'plone' : ['sendto', 'print', 'rss', 'extedit', 'full_screen'],
    'object_buttons' : ['cut', 'copy', 'paste', 'delete'],
    'folder_buttons' : ['cut', 'copy', 'paste', 'delete'],
}

def threeX_alpha1(context):
    """3.x -> 4.0alpha1
    """
    portal = getToolByName(context, 'portal_url').getPortalObject()
    loadMigrationProfile(context, 'profile-plone.app.upgrade:3-4alpha1')

    migrateActionIcons(portal)


def migrateActionIcons(portal):
    atool = getToolByName(portal, 'portal_actions', None)
    aitool = getToolByName(portal, 'portal_actionicons', None)

    if atool is None or aitool is None:
        return

    # Existing action categories
    categories = atool.objectIds()

    for ic in aitool.listActionIcons():
        cat = ic.getCategory()
        if cat in categories:
            ident = ic.getActionId()
            expr = ic.getExpression()
            action = atool[cat].get(ident)
            if action is not None:
                if not action.icon_expr:
                    prefix = ''
                    if not ':' in expr and cat in _KNOWN_ACTION_ICONS.keys():
                        if ident in _KNOWN_ACTION_ICONS[cat]:
                            prefix = 'string:$portal_url/'
                    action.icon_expr = '%s%s' % (prefix, expr)
                # Remove the action icon
                aitool.removeActionIcon(cat, ident)
