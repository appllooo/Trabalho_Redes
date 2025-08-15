import pygame
import socket
import threading
import json
import sys
import os
from dotenv import load_dotenv

WIDTH, HEIGHT = 800, 600
BLOCK_WIDTH, BLOCK_HEIGHT = 15, 100
BALL_RADIUS = 7
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT_SIZE = 32

load_dotenv()
SERVER_HOST = os.environ["HOST"]
SERVER_PORT = int(os.environ["PORT"])

game_state = {
    "ball": [WIDTH / 2, HEIGHT / 2],
    "player1_y": HEIGHT / 2 - BLOCK_HEIGHT / 2,
    "player2_y": HEIGHT / 2 - BLOCK_HEIGHT / 2,
    "score": [0, 0]
}
client_state = "MENU" 
my_player_id = -1
winner = -1
server_message = ""

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send_to_server(data):
    try:
        message = json.dumps(data) + '\n'
        client_socket.sendall(message.encode('utf-8'))
    except (BrokenPipeError, ConnectionResetError):
        print("Conexão com o servidor perdida.")
        pygame.quit()
        sys.exit()

def receive_from_server():
    global game_state, client_state, my_player_id, winner, server_message
    try:
        for line in client_socket.makefile('r'):
            data = json.loads(line)
            
            
            if data.get("type") == "GAME_STATE":
                game_state = data
            elif data.get("type") == "GAME_START":
                my_player_id = data.get("player_id")
                client_state = "PLAYING"
            elif data.get("type") == "GAME_OVER":
                winner = data.get("winner")
                client_state = "GAME_OVER"

            
            elif "status" in data:
                server_message = data.get("message")
                if data["status"] == "SUCCESS" and "criada" in server_message:
                    client_state = "WAITING"
                
    except (ConnectionAbortedError, ConnectionResetError):
        print("Desconectado do servidor.")
    finally:
        client_socket.close()

def draw_text(surface, text, x, y, font, color=WHITE):
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, (x, y))

def draw_menu(screen, font, input_boxes, active_box):
    screen.fill(BLACK)
    draw_text(screen, "Bem-vindo ao Pong Multiplayer!", 150, 50, font)
    
    for key, box in input_boxes.items():
        pygame.draw.rect(screen, WHITE, box['rect'], 2)
        draw_text(screen, box['label'], box['rect'].x + 5, box['rect'].y - 25, pygame.font.Font(None, 24))
        draw_text(screen, box['text'] , box['rect'].x + 5, box['rect'].y + 10, pygame.font.Font(None, 24))
        if key == active_box:
            
            pygame.draw.rect(screen, (100, 200, 255), box['rect'], 2)

    draw_text(screen, "1. Criar Partida", 100, 400, font)
    draw_text(screen, "2. Entrar na Partida", 100, 450, font)
    draw_text(screen, "3. Sair", 100, 500, font)

    draw_text(screen, server_message, 100, 550, pygame.font.Font(None, 24), (255, 255, 0))


def draw_game(screen, font):
    screen.fill(BLACK)
    
    player1 = pygame.Rect(10, game_state['player1_y'], BLOCK_WIDTH, BLOCK_HEIGHT)
    player2 = pygame.Rect(WIDTH - 10 - BLOCK_WIDTH, game_state['player2_y'], BLOCK_WIDTH, BLOCK_HEIGHT)
    pygame.draw.rect(screen, WHITE, player1)
    pygame.draw.rect(screen, WHITE, player2)
    
    pygame.draw.circle(screen, WHITE, (int(game_state['ball'][0]), int(game_state['ball'][1])), BALL_RADIUS)
    
    score_text = f"{game_state['score'][0]}   {game_state['score'][1]}"
    draw_text(screen, score_text, WIDTH // 2 - 50, 20, font)

def draw_waiting_screen(screen, font):
    screen.fill(BLACK)
    draw_text(screen, "Aguardando outro jogador...", 200, HEIGHT // 2 - 20, font)
    draw_text(screen, server_message, 100, HEIGHT // 2 + 30, pygame.font.Font(None, 24), (255, 255, 0))

def draw_game_over_screen(screen, font):
    screen.fill(BLACK)
    msg = f"Jogador {winner + 1} venceu!"
    draw_text(screen, "FIM DE JOGO", 300, HEIGHT // 2 - 40, font)
    draw_text(screen, msg, 280, HEIGHT // 2, font)
    draw_text(screen, "Pressione qualquer tecla para voltar ao menu.", 100, HEIGHT - 50, pygame.font.Font(None, 28))


def main():
    global client_state, server_message
    
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
    except ConnectionRefusedError:
        print("Não foi possível conectar ao servidor. Verifique se o servidor está rodando e o IP/porta estão corretos.")
        return

  
    receiver_thread = threading.Thread(target=receive_from_server, daemon=True)
    receiver_thread.start()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pong Multiplayer")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, FONT_SIZE)

    input_boxes = {
        'game_id': {'rect': pygame.Rect(100, 200, 300, 32), 'text': '', 'label': 'Nome da Partida: '},
        'password': {'rect': pygame.Rect(100, 300, 300, 32), 'text': '', 'label': 'Senha (opcional): '}
    }
    active_box = None

    running = True
    while running:
        my_player_y = game_state[f'player{my_player_id + 1}_y'] if my_player_id != -1 else HEIGHT / 2 - BLOCK_HEIGHT/2

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if client_state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for key, box in input_boxes.items():
                        if box['rect'].collidepoint(event.pos):
                            print("clicou em", key)
                            active_box = key
                            break
                        else:
                            active_box = None

                if event.type == pygame.KEYDOWN:
                    if active_box:
                        if event.key == pygame.K_BACKSPACE:
                            input_boxes[active_box]['text'] = input_boxes[active_box]['text'][:-1]
                        else:
                            input_boxes[active_box]['text'] += event.unicode
                    
                    if event.key == pygame.K_1: 
                        send_to_server({
                            "command": "CREATE_GAME",
                            "game_id": input_boxes['game_id']['text'],
                            "password": input_boxes['password']['text'] or None
                        })
                    if event.key == pygame.K_2: 
                        send_to_server({
                            "command": "JOIN_GAME",
                            "game_id": input_boxes['game_id']['text'],
                            "password": input_boxes['password']['text'] or None
                        })
                    if event.key == pygame.K_3: 
                        running = False
                        break
                        
            elif client_state == "GAME_OVER":
                 if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    client_state = "MENU"
                    server_message = ""
                    game_state["score"] = [0, 0]


        if client_state == "PLAYING":
            keys = pygame.key.get_pressed()
            new_y = my_player_y
            if keys[pygame.K_UP]:
                new_y -= 8
            if keys[pygame.K_DOWN]:
                new_y += 8
            
            new_y = max(0, min(new_y, HEIGHT - BLOCK_HEIGHT))

            if new_y != my_player_y:
                send_to_server({"command": "UPDATE_BLOCK", "y": new_y})
        
        if client_state == "MENU":
            draw_menu(screen, font, input_boxes, active_box)
        elif client_state == "WAITING":
            draw_waiting_screen(screen, font)
        elif client_state == "PLAYING":
            draw_game(screen, font)
        elif client_state == "GAME_OVER":
            draw_game_over_screen(screen, font)

        pygame.display.flip()
        clock.tick(60)

    send_to_server({"command": "FINISH_CONNECTION"})
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()