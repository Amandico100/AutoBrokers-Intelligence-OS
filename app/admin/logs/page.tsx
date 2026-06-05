'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { AlertCircle, CheckCircle2, FileText, RefreshCw, ShieldAlert } from 'lucide-react';

type LogStatus = 'success' | 'warning' | 'error' | string | null;

interface SystemLog {
  id: string;
  timestamp: string | null;
  user_id: string | null;
  admin_id: string | null;
  company_id: string | null;
  action_type: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  status: LogStatus;
  error_message: string | null;
}

function formatDate(value: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusBadge(status: LogStatus) {
  if (status === 'error') {
    return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Erro</Badge>;
  }
  if (status === 'warning') {
    return <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30">Aviso</Badge>;
  }
  return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Sucesso</Badge>;
}

function compactDetails(details: Record<string, unknown> | null) {
  if (!details || Object.keys(details).length === 0) return '-';
  const text = JSON.stringify(details);
  return text.length > 140 ? `${text.slice(0, 140)}...` : text;
}

export default function AdminLogsPage() {
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('all');

  const counts = useMemo(
    () => ({
      total: logs.length,
      success: logs.filter((log) => log.status === 'success').length,
      warning: logs.filter((log) => log.status === 'warning').length,
      error: logs.filter((log) => log.status === 'error').length,
    }),
    [logs],
  );

  const loadLogs = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ limit: '100' });
      if (status !== 'all') params.set('status', status);

      const response = await fetch(`/api/admin/logs?${params.toString()}`, {
        credentials: 'include',
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || 'Falha ao carregar logs do sistema');
      }

      setLogs(Array.isArray(data.logs) ? data.logs : []);
    } catch (err) {
      console.error('Error loading system logs:', err);
      setError(err instanceof Error ? err.message : 'Falha ao carregar logs do sistema');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [status]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Logs do Sistema</h1>
          <p className="text-muted-foreground mt-1">Eventos administrativos e de seguranca</p>
        </div>
        <Button onClick={loadLogs} disabled={loading} variant="outline">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{counts.total}</p>
            </div>
            <FileText className="w-5 h-5 text-blue-400" />
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Sucesso</p>
              <p className="text-2xl font-bold text-green-400">{counts.success}</p>
            </div>
            <CheckCircle2 className="w-5 h-5 text-green-400" />
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Avisos</p>
              <p className="text-2xl font-bold text-yellow-300">{counts.warning}</p>
            </div>
            <AlertCircle className="w-5 h-5 text-yellow-300" />
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Erros</p>
              <p className="text-2xl font-bold text-red-400">{counts.error}</p>
            </div>
            <ShieldAlert className="w-5 h-5 text-red-400" />
          </CardContent>
        </Card>
      </div>

      <Card className="bg-card border-border">
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>Eventos recentes</CardTitle>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-full sm:w-48 bg-muted border-border">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="success">Sucesso</SelectItem>
              <SelectItem value="warning">Aviso</SelectItem>
              <SelectItem value="error">Erro</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-300">
              {error}
            </div>
          ) : loading ? (
            <div className="py-12 text-center text-muted-foreground">Carregando logs...</div>
          ) : logs.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">Nenhum log encontrado.</div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Data</TableHead>
                    <TableHead>Acao</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Recurso</TableHead>
                    <TableHead>Detalhes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="whitespace-nowrap">{formatDate(log.timestamp)}</TableCell>
                      <TableCell className="font-medium">{log.action_type}</TableCell>
                      <TableCell>{statusBadge(log.status)}</TableCell>
                      <TableCell>{log.resource_type || '-'}</TableCell>
                      <TableCell className="max-w-xl text-xs text-muted-foreground">
                        {log.error_message || compactDetails(log.details)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
