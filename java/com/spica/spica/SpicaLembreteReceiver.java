package com.spica.spica;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.usage.UsageStats;
import android.app.usage.UsageStatsManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

// Lembrete das 23h para o "foguinho" do TikTok. Roda pelo AlarmManager, mesmo com o app fechado.
public class SpicaLembreteReceiver extends BroadcastReceiver {
    public static final String ACAO = "com.spica.spica.LEMBRETE_TIKTOK";
    private static final String PREFS = "spica_tiktok";
    private static final int ID_ALARME = 4242;
    private static final int ID_NOTIFICACAO = 4343;
    private static final String CANAL = "spica_lembretes";
    private static final int HORA = 23;
    private static final int MIN_FOGUINHO = 2;

    @Override
    public void onReceive(Context ctx, Intent intent) {
        try {
            if (intent != null && ACAO.equals(intent.getAction())) {
                verificarEAvisar(ctx);
            }
        } catch (Exception e) {
            // nunca derruba o app: o próximo alarme continua agendado
        }
        agendar(ctx);
    }

    // Agenda o próximo disparo para as 23h (hoje, se ainda não passou; senão amanhã).
    public static void agendar(Context ctx) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        Calendar c = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, HORA);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        if (System.currentTimeMillis() >= c.getTimeInMillis()) {
            c.add(Calendar.DAY_OF_MONTH, 1);
        }
        Intent i = new Intent(ACAO);
        i.setPackage(ctx.getPackageName());
        PendingIntent pi = PendingIntent.getBroadcast(ctx, ID_ALARME, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, c.getTimeInMillis(), pi);
    }

    private static String fmt(Calendar c) {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(c.getTime());
    }

    private static boolean eTikTok(String pacote) {
        String p = pacote.toLowerCase(Locale.US);
        return p.contains("musically") || p.contains("trill") || p.contains("zhiliao");
    }

    // 1 = abriu, 0 = não abriu, -1 = sem dados (permissão de uso de apps desligada)
    private static int abriuHoje(Context ctx) {
        UsageStatsManager usm = (UsageStatsManager) ctx.getSystemService(Context.USAGE_STATS_SERVICE);
        if (usm == null) return -1;
        Calendar inicio = Calendar.getInstance();
        inicio.set(Calendar.HOUR_OF_DAY, 0);
        inicio.set(Calendar.MINUTE, 0);
        inicio.set(Calendar.SECOND, 0);
        inicio.set(Calendar.MILLISECOND, 0);
        List<UsageStats> lista = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY,
                inicio.getTimeInMillis(), System.currentTimeMillis());
        if (lista == null || lista.isEmpty()) return -1;
        for (UsageStats u : lista) {
            String p = u.getPackageName();
            if (p != null && eTikTok(p) && u.getTotalTimeInForeground() > 0) return 1;
        }
        return 0;
    }

    private static void verificarEAvisar(Context ctx) {
        SharedPreferences prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String hoje = fmt(Calendar.getInstance());
        if (hoje.equals(prefs.getString("ultimo_check", ""))) return;
        int resultado = abriuHoje(ctx);
        prefs.edit().putString("ultimo_check", hoje).apply();
        if (resultado == -1) {
            notificar(ctx, "Para eu lembrar do TikTok, ligue o acesso ao uso de apps da Spica nas configurações do Android.");
            return;
        }
        Set<String> dias = new HashSet<>(prefs.getStringSet("dias", new HashSet<String>()));
        if (resultado == 1) {
            dias.add(hoje);
            prefs.edit().putStringSet("dias", dias).apply();
            return;
        }
        int sequencia = 0;
        Calendar dia = Calendar.getInstance();
        dia.add(Calendar.DAY_OF_MONTH, -1);
        while (dias.contains(fmt(dia))) {
            sequencia++;
            dia.add(Calendar.DAY_OF_MONTH, -1);
        }
        if (sequencia >= MIN_FOGUINHO) {
            notificar(ctx, "Você ainda não abriu o TikTok hoje e está com " + sequencia + " dias de foguinho. Quer manter?");
        }
    }

    private static void notificar(Context ctx, String texto) {
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(CANAL, "Lembretes da Spica",
                    NotificationManager.IMPORTANCE_DEFAULT));
            b = new Notification.Builder(ctx, CANAL);
        } else {
            b = new Notification.Builder(ctx);
        }
        b.setSmallIcon(android.R.drawable.ic_dialog_info)
         .setContentTitle("Spica")
         .setContentText(texto)
         .setAutoCancel(true);
        nm.notify(ID_NOTIFICACAO, b.build());
    }
}
