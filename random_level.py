import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from random import choice, randint


# ? Functions for all the characters
# * Returns a list as the 1st item is for if they are moving into it, the 2nd item is for if they are moving out of it
# * prev refers to if they are moving out of it or not
def empty(player, prev):
    return [1,1]

def wall(player, prev):
    return [0,1]

def key(player, prev):
    if not prev:
        print("\n~~~~ Key obtained! ~~~~")
        player['key'] = True
    return [1,0]

def stairs(player, prev):
    if player['key'] and not prev:
        print("\n~~~~ You won! ~~~~")
        player['done'] = True
    return [1,1]
 
def enemy(player, prev):
    if not prev:
        if player['sword']:
            print("\n~~~~ Enemy defeated! ~~~~")
            return [1,0]
        print("\n~~~~ You died! ~~~~")
        player['done'] = True
        return [0,0]
    return [1,0]

def sword(player, prev):
    if not prev:
        print("\n~~~~ Sword obtained! ~~~~")
        player['sword'] = True
    return [1,0]

# ? Lookup table for all the characters
characters = {
    "~": empty,
    "|": wall,
    "$": key,
    "^": stairs,
    "!": enemy,
    "?": sword
}


# ? Function used in the branching to check if it is possible to move to the next position
def move_check(gen, pos, special_chars, info):
    # * Checks if the player can actually move
    if pos[info['index']] == info['cap']:
        return 0
    # * Checks if the move is a wall or an enemy, uses walrus so we don't have to repeat
    elif (move := gen[pos[0]+(info['change'] if info['index'] == 0 else 0)][pos[1]+(info['change'] if info['index'] == 1 else 0)]) == "|" or move == "!":
        if move == "!":
            # * Seems redundant but will feed into the variations that allow for the enemy to block the path
            # ! Remove the next two lines to speed up generation
            if not special_chars["?"]:
                return 0
                
            special_chars["!"] = 1
        else:
            return 0
    elif move in ["$", "^", "?"]:
        # * Allows for variations where the enemy blocks the path but the sword is still reachable to defeat it
        # ! Remove the two lines to speed up generation
        if move != "?" and (not special_chars["?"] or not special_chars["!"]):
            return 0

        special_chars[move] = 1
    
    # * Not necessary but good for testing, marks position on the generation
    gen[pos[0]][pos[1]] = "."
    # * Change the position to the current in the branch
    pos[info['index']] += info['change']
    return pos
    

# ? Actual function for changing the position of the player and updating the generation
def move(player, gen, copy_gen, info):
    # * Like in the previous checks if the player can actually move into this position
    if player['pos'][info['index']] == info['cap']:
        return 0

    # * Finds the character for the new move
    move = gen[player['pos'][0]+(info['change'] if info['index'] == 0 else 0)][player['pos'][1]+(info['change'] if info['index'] == 1 else 0)]
    
    # * Calls the function for both the characters to run checks and to see what needs updating on the generation
    result = [characters[move](player, False)[0], characters[copy_gen[player['pos'][0]][player['pos'][1]]](player, True)[1]]

    # * If the new position needs changing to the player character
    if result[0]:
        gen[player['pos'][0]+(info['change'] if info['index'] == 0 else 0)][player['pos'][1]+(info['change'] if info['index'] == 1 else 0)] = "."
        
        # * If the old position needs changing back to what it used to be or an empty space
        if result[1]:
            gen[player['pos'][0]][player['pos'][1]] = copy_gen[player['pos'][0]][player['pos'][1]]
        else:
            gen[player['pos'][0]][player['pos'][1]] = "~"
        # * Changes the position
        player['pos'][info['index']] += info['change']


# ? Function for running the crawler to check if the generation is possible
def branch(gen, pos, special_chars, previous, moves):    
    # * Iterates through all of the moves to see if each move is possible
    for m in moves.values():
        # * Creates a new position so if it is changed it doesn't affect the old position
        new_pos = [pos[0], pos[1]]
        # * Checks if the move is possible and returns where the new position will be
        new_pos = move_check(gen, new_pos, special_chars, m)
        # * If the move is invalid or has been made before it will skip
        if not new_pos or new_pos in previous:
            continue
        previous.append(new_pos)
        # * Checks if all the conditions have been met and if so we can finish up
        if all(v for v in special_chars.values()):
            return True
        # * Branches again to continue down 
        done = branch(gen, new_pos, special_chars, previous, moves)

        # * If the branch was successful start closing down the branches
        if done:
            return True


def generate(rows, columns, moves):
    gen_verified = False
    while not gen_verified:
        copy_chars = ["~", "|"]
        special_chars = {"$":"", "^":"", "!":"", "?":""}
        # * Creates a base generation with the two basic characters
        generation = [[choice(copy_chars) for x in range(rows)] for y in range(columns)]
        # * Now it goes through each special key making sure they are in a position a decent distance away from the start and there is always one of each
        for key in special_chars:
            while (pos := [randint(0,columns-1), randint(0,rows-1)]) == [0,0] or pos in special_chars.values() or sum(pos) < 0.3 * (columns+rows): pass
            special_chars[key] = pos
            generation[pos[0]][pos[1]] = key
        # * Makes things easier so the player doesn't spawn on a wall (can't set spawn here as no function was created for the player character)
        generation[0][0] = "~"

        # * Creates two copies, oh boy I hate references sometimes
        copy_gen = [[x for x in y] for y in generation]
        copy_copy_gen = [[x for x in y] for y in generation] 

        # * Starts the first branch with all the base generation
        gen_verified = branch(copy_gen, [0, 0], {"$":0, "^":0, "!": 0, "?": 0}, [[0,0]], moves)
    return generation, copy_copy_gen

async def generate_start(loop, rows, columns, moves):
    executor = ProcessPoolExecutor(4)
    result, unfinished = await asyncio.wait([loop.run_in_executor(executor, generate, rows, columns, moves) for i in range(4)], return_when=asyncio.FIRST_COMPLETED)
    for r in result:
        generation, copy_copy_gen = r.result()

    return generation, copy_copy_gen

if __name__ == "__main__":
    again = True
    # ? A while loop so we can keep playing or quit when we finish
    while again:
        # * If you wanted smaller generations you could either remove enemy, sword, or key
        # * Or check if the product of the two are >5 rather than check both are >2
        while not (columns := input("Enter number of columns (must be >2): ")) or not columns.isdigit() or not ((columns := int(columns)) > 2): pass
        while not (rows := input("Enter number of rows (must be >2): ")) or not rows.isdigit() or not ((rows := int(rows)) > 2): pass
        # * All the available moves
        moves = {
            "l": {"index": 1, "change": -1, "cap": 0},
            "r": {"index": 1, "change": 1, "cap": rows-1},
            "u": {"index": 0, "change": -1, "cap": 0},
            "d": {"index": 0, "change": 1, "cap": columns-1}
        }
        # * The attributes needed for the player
        player = {"key": False, "done": False, "sword": False, "pos": [0,0]}

        print("Generating dungeon...")
        gen_verified = False
        # ? A while loop that continues until there is a successful generation
        loop = asyncio.get_event_loop()
        generation, copy_copy_gen = loop.run_until_complete(generate_start(loop, rows, columns, moves))
        
        # * Once the generation is finally done the player starting position is set
        generation[0][0] = "."
        print("\n~~~~ Welcome! ~~~~")
        input("~ = empty space\n| = wall\n$ = key\n^ = stairs\n! = enemy\n? = sword\n")
        # * Prints out the generation in a clean way
        print('\n'.join(' '.join(row for row in column) for column in generation))

        # * Loops until the game is over
        while not player['done']:
            while not (m := input("\nEnter your move (l, r, u, d): ")) or m not in moves: pass
            # * Finally it makes the move allowing the player to navigate the generation
            move(player, generation, copy_copy_gen, moves[m])
            print('\n'.join(' '.join(row for row in column) for column in generation))
        again = input("\nEnter any key to start over: ")