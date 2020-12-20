import os
import ifunny_lib as ifl


def main():
    ifl.load_auths(file="../auth_data")
    if not os.path.exists("post_data"):
        print(1, "downloading")
        post = ifl.post_from_url("https://ifunny.co/picture/what-what-what-the-away-fuck-the-fuck-fuck-b9qpWE0E8?gallery=user&query=PieceOfBread")
        post.smiles.tag_only_mode = 'nick'
        post.smiles.load()
        post.store_file('post_data')
    else:
        print(1, "found local")
        post = ifl.Post(file_name='post_data')
    print(2, len(post.smiles.stored_content), [a for a in post.smiles])


if __name__ == '__main__':
    main()
