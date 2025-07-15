import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { 
  Activity, 
  Clock, 
  Settings, 
  Instagram, 
  CheckCircle, 
  AlertCircle, 
  XCircle,
  Play,
  Trash2,
  RefreshCw,
  Database,
  Zap,
  Globe,
  Image as ImageIcon
} from "lucide-react";

interface SystemStatus {
  instagram_logado: boolean;
  gemini_configurado: boolean;
  proxima_busca: string;
  proximo_post: string;
  fila_postagem: number;
  ultimo_log: string;
}

interface PostItem {
  id: number;
  titulo: string;
  categoria: string;
  timestamp: string;
  fonte: string;
}

const Dashboard = () => {
  const [status, setStatus] = useState<SystemStatus>({
    instagram_logado: false,
    gemini_configurado: false,
    proxima_busca: "--:--",
    proximo_post: "--:--",
    fila_postagem: 0,
    ultimo_log: "Sistema iniciando..."
  });

  const [config, setConfig] = useState({
    news_api_key: "",
    gnews_api_key: "",
    currents_api_key: "",
    newsdata_api_key: "",
    instagram_username: "",
    instagram_password: "",
    gemini_api_key: "",
    buscar_intervalo: 30,
    postar_intervalo: 60,
    max_posts_dia: 10,
    usar_news_api: true,
    usar_gnews: true,
    usar_currents: true,
    usar_newsdata: true,
    opacidade: 0.6,
    termos_busca: "tecnologia, inteligência artificial"
  });

  const [filaPostagem, setFilaPostagem] = useState<PostItem[]>([
    {
      id: 1,
      titulo: "Avanços em Inteligência Artificial revolucionam o mercado",
      categoria: "Tecnologia",
      timestamp: "14:30",
      fonte: "News API"
    },
    {
      id: 2,
      titulo: "Nova descoberta em energia renovável promete mudanças",
      categoria: "Ciência",
      timestamp: "14:25",
      fonte: "GNews"
    }
  ]);

  const [logs, setLogs] = useState([
    { timestamp: "14:35:12", message: "Sistema iniciado com sucesso", type: "success" },
    { timestamp: "14:35:10", message: "Conectando ao Instagram...", type: "info" },
    { timestamp: "14:35:08", message: "Carregando configurações", type: "info" }
  ]);

  // Simular atualizações em tempo real
  useEffect(() => {
    const interval = setInterval(() => {
      setStatus(prev => ({
        ...prev,
        ultimo_log: new Date().toLocaleTimeString()
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handlePostarProximo = () => {
    if (filaPostagem.length > 0) {
      const item = filaPostagem[0];
      setFilaPostagem(prev => prev.slice(1));
      setLogs(prev => [{
        timestamp: new Date().toLocaleTimeString(),
        message: `Post "${item.titulo}" publicado com sucesso`,
        type: "success"
      }, ...prev]);
    }
  };

  const handleReprovarItem = (id: number) => {
    setFilaPostagem(prev => prev.filter(item => item.id !== id));
    setLogs(prev => [{
      timestamp: new Date().toLocaleTimeString(),
      message: `Item ${id} reprovado e removido da fila`,
      type: "warning"
    }, ...prev]);
  };

  const handleLimparFila = () => {
    setFilaPostagem([]);
    setLogs(prev => [{
      timestamp: new Date().toLocaleTimeString(),
      message: "Fila de postagem limpa",
      type: "info"
    }, ...prev]);
  };

  const getStatusColor = (isActive: boolean) => {
    return isActive ? "default" : "destructive";
  };

  const getLogTypeColor = (type: string) => {
    switch (type) {
      case "success": return "text-success";
      case "warning": return "text-warning";
      case "error": return "text-destructive";
      default: return "text-info";
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <Instagram className="h-8 w-8 text-primary" />
              Centro de Comandos - Instagram Auto
            </h1>
            <p className="text-muted-foreground">Sistema de automação para posts no Instagram</p>
          </div>
          <Button variant="outline" size="sm" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Atualizar
          </Button>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Instagram</CardTitle>
              <Instagram className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <Badge variant={getStatusColor(status.instagram_logado)} className={status.instagram_logado ? "bg-success text-success-foreground" : ""}>
                {status.instagram_logado ? "Conectado" : "Desconectado"}
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Gemini AI</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <Badge variant={getStatusColor(status.gemini_configurado)} className={status.gemini_configurado ? "bg-success text-success-foreground" : ""}>
                {status.gemini_configurado ? "Configurado" : "Não configurado"}
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Próxima Busca</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status.proxima_busca}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Fila de Posts</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{filaPostagem.length}</div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Configurações */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Configurações
              </CardTitle>
              <CardDescription>Configure as APIs e parâmetros do sistema</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="news-api">News API Key</Label>
                  <Input 
                    id="news-api"
                    type="password"
                    value={config.news_api_key}
                    onChange={(e) => setConfig(prev => ({ ...prev, news_api_key: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gemini-api">Gemini API Key</Label>
                  <Input 
                    id="gemini-api"
                    type="password"
                    value={config.gemini_api_key}
                    onChange={(e) => setConfig(prev => ({ ...prev, gemini_api_key: e.target.value }))}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="search-terms">Termos de Busca</Label>
                <Input 
                  id="search-terms"
                  value={config.termos_busca}
                  onChange={(e) => setConfig(prev => ({ ...prev, termos_busca: e.target.value }))}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Intervalo de Busca (min): {config.buscar_intervalo}</Label>
                  <Slider
                    value={[config.buscar_intervalo]}
                    onValueChange={(value) => setConfig(prev => ({ ...prev, buscar_intervalo: value[0] }))}
                    max={120}
                    min={10}
                    step={5}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Opacidade da Imagem: {config.opacidade}</Label>
                  <Slider
                    value={[config.opacidade]}
                    onValueChange={(value) => setConfig(prev => ({ ...prev, opacidade: value[0] }))}
                    max={1}
                    min={0}
                    step={0.1}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={config.usar_news_api}
                    onCheckedChange={(checked) => setConfig(prev => ({ ...prev, usar_news_api: checked }))}
                  />
                  <Label>Usar News API</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={config.usar_gnews}
                    onCheckedChange={(checked) => setConfig(prev => ({ ...prev, usar_gnews: checked }))}
                  />
                  <Label>Usar GNews</Label>
                </div>
              </div>

              <Button className="w-full">Salvar Configurações</Button>
            </CardContent>
          </Card>

          {/* Fila de Postagem */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Fila de Postagem
                </span>
                <div className="flex gap-2">
                  <Button size="sm" onClick={handlePostarProximo} disabled={filaPostagem.length === 0}>
                    <Play className="h-4 w-4 mr-1" />
                    Postar Próximo
                  </Button>
                  <Button size="sm" variant="destructive" onClick={handleLimparFila}>
                    <Trash2 className="h-4 w-4 mr-1" />
                    Limpar Fila
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Título</TableHead>
                      <TableHead>Categoria</TableHead>
                      <TableHead>Fonte</TableHead>
                      <TableHead>Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filaPostagem.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium max-w-[200px] truncate">
                          {item.titulo}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{item.categoria}</Badge>
                        </TableCell>
                        <TableCell>{item.fonte}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button size="sm" variant="outline">
                              <Play className="h-3 w-3" />
                            </Button>
                            <Button 
                              size="sm" 
                              variant="destructive"
                              onClick={() => handleReprovarItem(item.id)}
                            >
                              <XCircle className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {filaPostagem.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    Nenhum item na fila de postagem
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Logs de Atividade */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Log de Atividades
            </CardTitle>
            <CardDescription>Últimas atividades do sistema</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              <div className="space-y-2">
                {logs.map((log, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
                    <span className="text-xs text-muted-foreground font-mono">
                      {log.timestamp}
                    </span>
                    <Separator orientation="vertical" className="h-4" />
                    <span className={`text-sm ${getLogTypeColor(log.type)}`}>
                      {log.message}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;