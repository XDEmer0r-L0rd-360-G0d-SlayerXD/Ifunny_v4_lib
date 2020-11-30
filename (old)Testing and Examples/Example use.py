import ifunny_lib as ifl
import os
from pprint import pprint
from pprint import pformat
import time


def goto_dir(dir: str):
    """
    Not part of the demonstration, this is just a helper func for me
    """
    if not os.path.exists(dir):
        os.mkdir(dir)
    os.chdir(dir)
    return


def nested_formatter(thing, current_depth=0):
    """
    This takes nested objects in tree form (name, ((name, nested), (name, nested))) and turns it into a string
    :param thing:
    :return:
    """
    indent_size = 3
    text = " "*indent_size*current_depth + f"{thing[0][0]}: {thing[0][2]} [{thing[0][1]}]\n"
    for a in thing[1]:
        text += nested_formatter(a)
    return text


def tree_cleaner(tree):
    """
    This is for getting out the data I want from a comment tree. This is specific to this example and assumes it is
    passed cdata as headers, and I want name, comment id, content of comment, and anything nested.
    :param tree: The tree with the objects
    :return:
    """
    new_tree = []
    for a in tree[1]:
        new_tree.append(tree_cleaner(a))
    return (tree[0]["name"], tree[0]["id"], tree[0]['text']), new_tree


def get_feats():
    """
    Get the last 10 features and store their pics/vids in get feats folder
    :return:
    """
    goto_dir('get feats')

    feats = ifl.get_features(10)

    for i, a in enumerate(feats):
        # pprint(a.cdata)
        ifl.dl_from_link(a.url, str(i) + '.' + a.url.split('.')[-1])

    os.chdir('..')


def get_comments_from_a_post_in_subfeed():
    """
    Using helper functions to print all comments of a post from the sub feed
    """
    me = ifl.Account()
    feed = me.sub_feed.load(100)
    chosen_post = feed[20]
    chosen_post.load_comment_tree()
    print("link:" + chosen_post.link, )
    # pprint(chosen_post.comment_id_tree())
    ifl.recursive_id_print(chosen_post, chosen_post.comment_id_tree())


def get_subscriptions_of_last_guest():
    me = ifl.Account()
    snooper = me.guests.load(2)[0]
    print(snooper.name, snooper.id)
    # snooper = ifl.User()
    snooper.subscriptions.load(100)  # because when testing the current guy hat 2.6k
    for a in snooper.subscriptions:
        print(a.name)


def save_post(post_id):
    thing = ifl.Post(post_id)  # have base object
    goto_dir(thing.id)  # make folder in cd with the id as name
    ifl.dl_from_link(thing.url, "Content." + thing.url.split('.')[-1])  # download the content, image or vid, and save it as Content.extension
    thing.store_file("Raw Post Data.txt")
    with open("Readable Post Data.txt", "w") as f:
        f.write(pformat(thing.cdata))
    thing.comments.load()
    for a in thing.comments:
        a.replies.load()
    with open("Raw Comment Tree.txt", 'w', encoding="utf-16") as f:
        for a in thing.comments:
            try:
                f.write(str(a.cdata) + '\n')
            except:
                print("Errored on:", a.cdata)
                str(a.cdata)
                input(">")

    with open("Readable Comment Tree.txt", 'w', encoding='utf-16') as f:
        for a in thing.comments:
            f.write(a.text + '\n')
            for b in a.replies:
                f.write(b.depth * "  " + b.creator_name + ": " + b.text + '\n')
                # print(b.depth)
    os.chdir("..")


def archive_user(username):
    author = ifl.User(ifl.get_author_id(username))
    goto_dir(author.name)
    print('saving main data.')
    author.store_file(author.name + ".txt")
    print('done.')
    print("loading subscribtions.")
    author.subscriptions.tag_only_mode = "nick"
    author.subscriptions.load()
    print('saving.')
    author.subscriptions.save_to_file("subscriptions.txt")
    print("done.")
    print('loading subscribers')
    author.subscribers.tag_only_mode = "nick"
    author.subscribers.load()
    print('saving.')
    author.subscribers.save_to_file("subscribers.txt")
    print('done.')
    print('loading posts.')
    author.posts.load()
    temp_len = len(author.posts)
    count = 40
    for num_a, a in enumerate(author.posts):
        if count > 0:
            count -= 1
            continue
        now = time.time()
        if "id" not in a.errored_attributes:
            print(f'saving {a.id}: {num_a}/{temp_len}')
            goto_dir(a.id)
            ifl.dl_from_link(a.url, "Content." + a.url.split('.')[-1])
            a.store_file("Post data.txt")
            print('smiles')
            a.smiles.tag_only_mode = 'nick'
            a.smiles.load()
            a.smiles.save_to_file("smiles.txt")
            print('repubs')
            a.repubs.tag_only_mode = 'nick'
            a.repubs.load()
            a.repubs.save_to_file("repubs.txt")
            print('comments')
            a.comments.load()
            out = ""
            for b in a.comments:
                try:
                    out += b.name + ': ' + b.text + '\n'
                except:
                    out += "[removed]\n"
                b.replies.load()
                for c in b.replies:
                    try:
                        out += '   '*c.depth + c.creator_id + ': ' + c.text + '\n'
                    except:
                        out += '   '*c.depth + '[removed]\n'
            with open('Comments.txt', 'w', encoding="utf-16") as f:
                f.write(out)
            os.chdir('..')
            print(time.time() - now)
    print('done.')


def main():
    """
    Uncomment these to have them run to show that they work
    """
    ifl.load_auths()
    goto_dir('Example Data')
    # get_feats()
    # get_comments_from_a_post_in_subfeed()
    # get_subscriptions_of_last_guest()
    thing = ifl.post_from_url("https://ifunny.co/picture/keep-reacting-to-my-memes-and-we-gonna-end-up-5q08lSXx7?gallery=user&query=billowywarcraft")
    # print(thing.id)
    # save_post(thing.id)
    start = time.time()
    archive_user("billowywarcraft")
    print(time.time() - start)


if __name__ == '__main__':
    main()
    # ifl.load_auths()
    # hold = ifl.Post("NSRM3Edh7")
    # hold.comments.load()
    # com = ifl.Comment("NSRM3Edh7", "5ed40dcef4638846d3662a2b")
    # for a in hold.comments:
    #     if "last_reply" in a.cdata:
    #         del a.cdata["last_reply"]
    #     # pprint(a.cdata)
    # pprint(com.cdata)
