"""Create a disposable synthetic inbox; never import a personal workspace."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'src'))
from macrotrading.service import Service
from macrotrading.validation import canonical, digest, stamp

service = Service(root, sys.argv[1])
now = datetime.now(timezone.utc)
candidate = {
    'id': 'tutorial-policy-candidate',
    'title': 'TUTORIAL FIXTURE — example policy observation',
    'summary': 'Synthetic teaching example only. Review the classification and source before accepting evidence. This is not a real policy announcement.',
    'url': 'https://example.com/tutorial-fixture',
    'published_at': stamp(now - timedelta(hours=1)),
    'retrieved_at': stamp(now - timedelta(minutes=1)),
    'content_hash': digest('MacroTrading synthetic tutorial source'),
    'source_group': 'tutorial-fixture',
    'suggested_themes': ['japan_normalization'],
    'kind': 'unclassified',
    'review_required': True,
}
with service.store.transaction() as db:
    db.execute('INSERT INTO inbox(id,source_id,first_known_at,payload) VALUES(?,?,?,?)',
               (candidate['id'], 'tutorial-fixture', candidate['retrieved_at'], canonical(candidate)))
    service.store.audit(db, 'Synthetic tutorial inbox seeded', {'candidate_id': candidate['id']})
print('Disposable demo inbox ready; no sources fetched.')
