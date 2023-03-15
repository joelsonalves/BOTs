from playwright.sync_api import sync_playwright
import pandas as pd

AGUARDANDO_PROCESSAMENTO    = 0
CURSANDO                    = 1
CONCLUINTE                  = 2
DESISTENTE                  = 3
HOMONIMO                    = 4

LISTA_PARA_TROCA_DE_CARACTERES = [
    ['A', ['Á', 'À', 'Ã', 'Â', 'Ä']],
    ['E', ['É', 'È', 'Ẽ', 'Ê', 'Ë']],
    ['I', ['Í', 'Ì', 'Ĩ', 'Î', 'Ï']],
    ['O', ['Ó', 'Ò', 'Õ', 'Ô', 'Ö']],
    ['U', ['Ú', 'Ù', 'Ũ', 'Û', 'Ü']],
    ['N', ['Ñ']],
    ['C', ['Ç']]
]

class Bot():

    def __init__(self):
        super().__init__()
        self.__pagina_inicial = 'https://censobasico.inep.gov.br'
        self.__pagina_apos_login = 'https://censobasico.inep.gov.br/censobasico/#/inicioMatricula'
        self.__pagina_lista_de_turmas = 'https://censobasico.inep.gov.br/censobasico/#/turma/listar'
        self.__lista_de_estudantes = []
        self.__lista_resultado = []
        self.__arquivo_csv = 'lista_sisacad_censo_2022.csv'

    def __ajustar_texto(self, texto):
        texto = texto.strip().replace('  ', ' ').upper()
        for linha in LISTA_PARA_TROCA_DE_CARACTERES:
            for c in linha[1]:
                texto = texto.replace(c, linha[0])
        for c in texto:
            if not ((c >= 'A' and c <= 'Z') or c == ' '):
                texto = texto.replace(c, '') 
        return texto
    
    def __verificar_se_o_navegador_ainda_esta_funcional(self, page):
        try:
            page.title()
        except BaseException:
            return False
        return True

    def __fazer_login(self, page):
        page.goto(self.__pagina_inicial)   
        print('Aguardando login no CENSO...')
        
        while (True):
            page.wait_for_timeout(1000)
            if (page.url == self.__pagina_apos_login):
                break
        
        page.goto(self.__pagina_lista_de_turmas)

    def __extrair_lista_de_estudantes(self, page):
        self.__lista_de_estudantes = []
        self.__lista_de_estudantes = page.evaluate(''' () => { var lista = []; document.querySelectorAll('td.text-center.col-md-3.ng-binding').forEach((linha) => { lista.push(linha.innerText); }); return lista; } ''')

        for i in range(len(self.__lista_de_estudantes)):
            self.__lista_de_estudantes[i] = self.__lista_de_estudantes[i].split('\n')[0].split(' - ')[1]

        for i in range(len(self.__lista_de_estudantes)):
            self.__lista_de_estudantes[i] = self.__ajustar_texto(self.__lista_de_estudantes[i])

    def __comparar_lista_de_estudantes(self):

        if len(self.__lista_de_estudantes) > 0:

            self.__lista_resultado = []
            for i in range(len(self.__lista_de_estudantes)):
                self.__lista_resultado.append(0)

            df_sisacad = pd.read_csv(self.__arquivo_csv, encoding='latin-1', sep=';', dtype=str)

            for i in df_sisacad.index:
                df_sisacad.loc[i, 'nome'] = self.__ajustar_texto(df_sisacad.loc[i, 'nome'])

            for i in range(len(self.__lista_de_estudantes)):
                linha = df_sisacad.loc[df_sisacad['nome']==self.__lista_de_estudantes[i]]
                quant_linhas = linha.shape[0]
                if quant_linhas > 1:
                    self.__lista_resultado[i] = HOMONIMO
                elif linha.shape[0] == 1:
                    if linha['nome_situacao_vincl'].values[0] == 'Concluído':
                        self.__lista_resultado[i] = CONCLUINTE
                    else:
                        self.__lista_resultado[i] = DESISTENTE
                else:
                    self.__lista_resultado[i] = CURSANDO
                
            df = None

    def __atualizar_situacao_no_censo(self, page):

        for i in range(len(self.__lista_resultado)):

            if self.__lista_resultado[i] == CURSANDO:
                page.locator('input[ng-model="aluno.cursoEmAndamento"]').nth(i).click()

            elif self.__lista_resultado[i] == CONCLUINTE:
                page.locator('input[ng-model="aluno.rendimentoAprovado"]').nth(i).click()
                page.locator('input[ng-model="aluno.concluinteSim"]').nth(i).click()

            elif self.__lista_resultado[i] == DESISTENTE:
                page.locator('input[ng-model="aluno.movimentoDeixouDeFrequentar"]').nth(i).click()

            elif self.__lista_resultado[i] == HOMONIMO:
                print(f'{self.__lista_de_estudantes[i]} ({i + 1}): HOMÔNIMO')

            elif self.__lista_resultado[i] == AGUARDANDO_PROCESSAMENTO:
                print(f'{self.__lista_de_estudantes[i]} ({i + 1}): AGUARDANDO PROCESSAMENTO')
        
    def run():

        falha_critica = False

        with sync_playwright() as p:

            print('\nBot de Apoio ao CENSO...\n')
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            context.clear_cookies()
            page = context.new_page()
            bot = Bot()

            try:

                bot.__fazer_login(page)

            except Exception:

                if not bot.__verificar_se_o_navegador_ainda_esta_funcional(page):

                    print('!!! HOUVE UMA FALHA CRÍTICA NO LOGIN !!!\n')
                    falha_critica = True

                else:

                    print('!!! HOUVE UMA FALHA NO LOGIN !!!\n')

            except BaseException:

                print('!!! HOUVE UMA FALHA CRÍTICA NO LOGIN !!!\n')
                falha_critica = True

            sequencia_de_processamento = 0

            while not falha_critica:

                sequencia_de_processamento += 1

                if not bot.__verificar_se_o_navegador_ainda_esta_funcional(page):

                    print('!!! HOUVE UMA FALHA CRÍTICA NO PROCESSAMENTO !!!\n')
                    falha_critica = True
                    break

                entrada = input(f'\nSequência de Processamento: {str(sequencia_de_processamento).zfill(4)} | Tecle [ENTER] para processar ou digite "SAIR" seguindo de [ENTER] para encerrar... ')

                if not entrada.upper() == 'SAIR':

                    try:

                        bot.__extrair_lista_de_estudantes(page)
                        bot.__comparar_lista_de_estudantes()
                        bot.__atualizar_situacao_no_censo(page)

                    except Exception:

                        if not bot.__verificar_se_o_navegador_ainda_esta_funcional(page):

                            print('!!! HOUVE UMA FALHA CRÍTICA NO LOGIN !!!\n')
                            falha_critica = True
                            break

                        else:

                            print('!!! HOUVE UMA FALHA NO PROCESSAMENTO !!!\n')

                    except BaseException:

                        print('!!! HOUVE UMA FALHA CRÍTICA NO PROCESSAMENTO !!!\n')
                        falha_critica = True
                        break

                else:
                    break
                    
            if not falha_critica:
                print('Finalizando Bot...')

                try:

                    page.set_default_timeout(5000)
                    page.close()
                    browser.close()

                except Exception:

                    print('!!! HOUVE UMA FALHA NA FINALIZAÇÃO !!!\n')

                except BaseException:

                    print('!!! HOUVE UMA FALHA CRÍTICA NA FINALIZAÇÃO !!!\n')

            page = None
            context = None
            browser = None
            bot = None

            print('Bot encerrado.')  

if __name__ == '__main__':

    Bot.run()