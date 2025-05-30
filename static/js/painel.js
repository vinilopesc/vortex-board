// static/js/painel.js
// Scripts específicos para o painel principal

// Variáveis globais
let modalNovoProjetoAberto = false;
let modalNotificacoesAberto = false;

/**
 * Inicializa os event listeners do painel
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Painel carregado');

    // Inicializar componentes
    initializeTooltips();
    initializeAnimations();
    setupKeyboardShortcuts();

    // Auto-refresh de estatísticas a cada 5 minutos
    setInterval(refreshStats, 300000);
});

/**
 * Abre modal para criar novo projeto
 */
function abrirModalNovoProjeto() {
    const modal = document.getElementById('modal-novo-projeto');
    if (!modal) return;

    modal.classList.remove('hidden');
    modalNovoProjetoAberto = true;

    // Carregar formulário via AJAX
    carregarFormularioProjeto();

    // Adicionar classe para animação
    setTimeout(() => {
        modal.querySelector('.relative').classList.add('fade-in');
    }, 10);
}

/**
 * Fecha modal de novo projeto
 */
function fecharModalNovoProjeto() {
    const modal = document.getElementById('modal-novo-projeto');
    if (!modal) return;

    modal.classList.add('hidden');
    modalNovoProjetoAberto = false;

    // Limpar conteúdo
    const content = document.getElementById('modal-novo-projeto-content');
    if (content) {
        content.innerHTML = '';
    }
}

/**
 * Abre modal de notificações
 */
function abrirModalNotificacoes() {
    const modal = document.getElementById('modal-notificacoes');
    if (!modal) return;

    modal.classList.remove('hidden');
    modalNotificacoesAberto = true;

    // Marcar notificações como visualizadas
    marcarNotificacoesVisualizadas();
}

/**
 * Fecha modal de notificações
 */
function fecharModalNotificacoes() {
    const modal = document.getElementById('modal-notificacoes');
    if (!modal) return;

    modal.classList.add('hidden');
    modalNotificacoesAberto = false;
}

/**
 * Carrega formulário de criação de projeto via AJAX
 */
function carregarFormularioProjeto() {
    const content = document.getElementById('modal-novo-projeto-content');
    if (!content) return;

    // Mostrar loading
    content.innerHTML = `
        <div class="text-center py-8">
            <div class="spinner mx-auto mb-4"></div>
            <p class="text-gray-600">Carregando formulário...</p>
        </div>
    `;

    // Simular carregamento (substituir por URL real)
    setTimeout(() => {
        content.innerHTML = `
            <div class="relative">
                <div class="flex items-center justify-between pb-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900">➕ Novo Projeto</h3>
                    <button onclick="fecharModalNovoProjeto()" class="text-gray-400 hover:text-gray-600">
                        ✕
                    </button>
                </div>

                <form class="mt-6 space-y-4" onsubmit="criarProjeto(event)">
                    <div>
                        <label for="nome" class="block text-sm font-medium text-gray-700 mb-1">
                            Nome do Projeto *
                        </label>
                        <input type="text" id="nome" name="nome" required
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                               placeholder="Ex: Sistema de Vendas">
                    </div>

                    <div>
                        <label for="cliente" class="block text-sm font-medium text-gray-700 mb-1">
                            Cliente *
                        </label>
                        <input type="text" id="cliente" name="cliente" required
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                               placeholder="Ex: Empresa XYZ Ltda">
                    </div>

                    <div>
                        <label for="descricao" class="block text-sm font-medium text-gray-700 mb-1">
                            Descrição
                        </label>
                        <textarea id="descricao" name="descricao" rows="3"
                                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  placeholder="Descreva o projeto..."></textarea>
                    </div>

                    <div class="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
                        <button type="button" onclick="fecharModalNovoProjeto()"
                                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                            Cancelar
                        </button>
                        <button type="submit"
                                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                            Criar Projeto
                        </button>
                    </div>
                </form>
            </div>
        `;
    }, 500);
}

/**
 * Cria novo projeto (placeholder)
 */
function criarProjeto(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const dados = {
        nome: formData.get('nome'),
        cliente: formData.get('cliente'),
        descricao: formData.get('descricao')
    };

    console.log('📝 Criando projeto:', dados);

    // Simular criação (substituir por requisição real)
    setTimeout(() => {
        fecharModalNovoProjeto();
        showNotification('Projeto criado com sucesso!', 'success');

        // Recarregar página ou atualizar lista
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }, 1000);
}

/**
 * Marca notificações como visualizadas
 */
function marcarNotificacoesVisualizadas() {
    // TODO: Implementar requisição para marcar como lidas
    console.log('👁️ Marcando notificações como visualizadas');

    // Remover badge de notificação
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.style.opacity = '0.5';
    }
}

/**
 * Atualiza estatísticas do painel
 */
function refreshStats() {
    console.log('🔄 Atualizando estatísticas...');

    // TODO: Implementar requisição AJAX para buscar stats atualizadas
    // fetch('/api/painel/stats/')
    //     .then(response => response.json())
    //     .then(data => updateStatsDisplay(data))
    //     .catch(error => console.error('Erro ao atualizar stats:', error));
}

/**
 * Atualiza display das estatísticas
 */
function updateStatsDisplay(stats) {
    // Atualizar contadores
    const elementos = {
        'projetos_ativos': stats.projetos_ativos,
        'minhas_tarefas': stats.minhas_tarefas,
        'bugs_ativos': stats.bugs_ativos,
        'horas_semana': stats.horas_semana
    };

    Object.keys(elementos).forEach(key => {
        const elemento = document.querySelector(`[data-stat="${key}"]`);
        if (elemento) {
            animateCounter(elemento, elementos[key]);
        }
    });
}

/**
 * Anima contador de estatísticas
 */
function animateCounter(elemento, valorFinal) {
    const valorInicial = parseInt(elemento.textContent) || 0;
    const incremento = (valorFinal - valorInicial) / 20;
    let atual = valorInicial;

    const timer = setInterval(() => {
        atual += incremento;
        elemento.textContent = Math.round(atual);

        if (Math.abs(atual - valorFinal) < 1) {
            elemento.textContent = valorFinal;
            clearInterval(timer);
        }
    }, 50);
}

/**
 * Inicializa tooltips
 */
function initializeTooltips() {
    const elementos = document.querySelectorAll('[data-tooltip]');

    elementos.forEach(elemento => {
        elemento.addEventListener('mouseenter', showTooltip);
        elemento.addEventListener('mouseleave', hideTooltip);
    });
}

/**
 * Mostra tooltip
 */
function showTooltip(event) {
    const texto = event.target.getAttribute('data-tooltip');
    if (!texto) return;

    const tooltip = document.createElement('div');
    tooltip.className = 'absolute bg-gray-900 text-white text-xs rounded py-1 px-2 z-50';
    tooltip.textContent = texto;
    tooltip.id = 'tooltip-temp';

    document.body.appendChild(tooltip);

    // Posicionar tooltip
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
}

/**
 * Esconde tooltip
 */
function hideTooltip() {
    const tooltip = document.getElementById('tooltip-temp');
    if (tooltip) {
        tooltip.remove();
    }
}

/**
 * Inicializa animações de entrada
 */
function initializeAnimations() {
    // Animar cards com delay escalonado
    const cards = document.querySelectorAll('.projeto-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';

        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

/**
 * Configura atalhos de teclado
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + K para abrir modal de notificações
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            abrirModalNotificacoes();
        }

        // Ctrl/Cmd + N para novo projeto (apenas gerentes/admins)
        if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
            const botaoNovo = document.querySelector('[onclick="abrirModalNovoProjeto()"]');
            if (botaoNovo) {
                event.preventDefault();
                abrirModalNovoProjeto();
            }
        }

        // ESC para fechar modais
        if (event.key === 'Escape') {
            if (modalNovoProjetoAberto) {
                fecharModalNovoProjeto();
            }
            if (modalNotificacoesAberto) {
                fecharModalNotificacoes();
            }
        }
    });
}

/**
 * Mostra notificação toast
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `
        fixed top-4 right-4 z-50 max-w-sm bg-white border rounded-lg shadow-lg p-4
        transform transition-all duration-300 ease-in-out translate-x-full
        ${type === 'success' ? 'border-green-400' : ''}
        ${type === 'error' ? 'border-red-400' : ''}
        ${type === 'warning' ? 'border-yellow-400' : ''}
        ${type === 'info' ? 'border-blue-400' : ''}
    `;

    notification.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <span class="mr-2">
                    ${type === 'success' ? '✅' : ''}
                    ${type === 'error' ? '❌' : ''}
                    ${type === 'warning' ? '⚠️' : ''}
                    ${type === 'info' ? 'ℹ️' : ''}
                </span>
                <span class="text-sm text-gray-700">${message}</span>
            </div>
            <button onclick="this.parentElement.parentElement.remove()"
                    class="text-gray-400 hover:text-gray-600 ml-2">
                ✕
            </button>
        </div>
    `;

    document.body.appendChild(notification);

    // Animar entrada
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);

    // Auto remover
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }, duration);
}

/**
 * Navegar para projeto
 */
function navegarParaProjeto(projetoId, boardId) {
    // Adicionar loading ao card
    const card = event.currentTarget;
    card.style.opacity = '0.6';

    // Navegar
    setTimeout(() => {
        window.location.href = `/board/${boardId}/`;
    }, 200);
}

/**
 * Exportar funcionalidades globalmente
 */
window.abrirModalNovoProjeto = abrirModalNovoProjeto;
window.fecharModalNovoProjeto = fecharModalNovoProjeto;
window.abrirModalNotificacoes = abrirModalNotificacoes;
window.fecharModalNotificacoes = fecharModalNotificacoes;
window.showNotification = showNotification;
window.navegarParaProjeto = navegarParaProjeto;

// Debug: Log quando arquivo é carregado
console.log('📁 painel.js carregado');