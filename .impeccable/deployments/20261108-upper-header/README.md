# Production: upper header only

User approved only the upper crest/logo and controls tier, without the Italian flag stripe. Applied by appending upper-tier-scoped CSS to the existing production static/css/club-rail.css. No local working-tree template, footer, navigation, homepage or backend changes were deployed.

Backup on server: /var/backups/kitaly/upper-header-20261108T172045Z.css
Deployed SHA256: 15c453dc7500f919cc9e5ec3b15271e9fe5b058d2a864537e0b97b9a510428fb
Public CSS verified byte-for-byte against the prepared patch. The original production CSS remains an exact prefix. Desktop and mobile rendered before deployment; live desktop checked after deployment. Navigation row DOM, colours and height unchanged in preview comparison. Submenu and theme switch verified live.

This is intentionally a narrow production patch; unrelated local changes remain un-deployed.
