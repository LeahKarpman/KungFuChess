import sys

from game import Game


def main():
    game = Game()

    try:
        game.load(sys.stdin.read())
        game.run()
    except ValueError as error:
        print("ERROR", error)


if __name__ == "__main__":
    main()
