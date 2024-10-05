import argparse

from database.models import PostedLink, PostedLinkV2, db_links_v2

arg_parser = argparse.ArgumentParser(description='Import links in to v2 db from v1')
arg_parser.parse_args()

link: PostedLink
count = 0
count_fail = 0
with db_links_v2.transaction() as txn:
    for link in PostedLink.select().iterator():
        try:
            PostedLinkV2.create_link(link.link, link.hits)
            count += 1
        except Exception as e:
            print(link.link, e)
            count_fail += 1
    txn.commit()

print(f'Migrated {count} links, {count_fail} failed')
