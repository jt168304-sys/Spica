package com.spica;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.IBinder;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import androidx.core.app.NotificationCompat;

/**
 * SpicaOverlayService — Floating bubble que aparece sobre TODOS os apps.
 * Tipo: Foreground Service com TYPE_APPLICATION_OVERLAY.
 * Para abrir o chat: toca na bolha (abre o app principal).
 * Para mover: arrasta a bolha.
 * Para remover: o app principal chama stopService().
 */
public class SpicaOverlayService extends Service {

    private static final String CHANNEL_ID   = "spica_overlay";
    private static final int    NOTIF_ID     = 1001;
    private static final int    BUBBLE_SIZE  = 180; // px

    private WindowManager   windowManager;
    private View            bubbleView;
    private WindowManager.LayoutParams params;

    // Arraste
    private int initialX, initialY;
    private float initialTouchX, initialTouchY;
    private long touchDownTime;

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    @Override
    public void onCreate() {
        super.onCreate();
        criarNotificacao();
        criarBolha();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (bubbleView != null && windowManager != null) {
            try { windowManager.removeView(bubbleView); } catch (Exception ignored) {}
        }
    }

    // ── Notificação obrigatória (Foreground Service) ───────────────────────────

    private void criarNotificacao() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel canal = new NotificationChannel(
                CHANNEL_ID, "Spica Overlay",
                NotificationManager.IMPORTANCE_MIN
            );
            canal.setShowBadge(false);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(canal);
        }

        Intent abrirApp = new Intent(this, getMainActivityClass());
        abrirApp.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
            ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            : PendingIntent.FLAG_UPDATE_CURRENT;
        PendingIntent pi = PendingIntent.getActivity(this, 0, abrirApp, flags);

        Notification notif = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Spica")
            .setContentText("Bolha ativa")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pi)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .build();

        startForeground(NOTIF_ID, notif);
    }

    // ── Criar bolha flutuante ──────────────────────────────────────────────────

    private void criarBolha() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        // Tipo correto para overlay sobre todos os apps (Android 8+)
        int tipo = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            : WindowManager.LayoutParams.TYPE_PHONE;

        params = new WindowManager.LayoutParams(
            BUBBLE_SIZE, BUBBLE_SIZE,
            tipo,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        );
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 0;
        params.y = 300;

        // View da bolha — círculo azul simples
        // Você pode substituir por um ImageView com o design V-Tuber depois
        bubbleView = criarViewBolha();
        bubbleView.setOnTouchListener(this::onTouch);

        windowManager.addView(bubbleView, params);
    }

    private View criarViewBolha() {
        // Círculo azul simples como placeholder
        // SUBSTITUIR: troque por ImageView com seu asset V-Tuber
        android.widget.FrameLayout frame = new android.widget.FrameLayout(this);
        frame.setLayoutParams(new android.widget.FrameLayout.LayoutParams(BUBBLE_SIZE, BUBBLE_SIZE));

        // Fundo circular
        android.graphics.drawable.GradientDrawable circle = new android.graphics.drawable.GradientDrawable();
        circle.setShape(android.graphics.drawable.GradientDrawable.OVAL);
        circle.setColor(Color.parseColor("#2D6FBA"));
        circle.setStroke(4, Color.WHITE);
        frame.setBackground(circle);

        // Ícone de estrela no centro (placeholder — substituir pelo asset V-Tuber)
        android.widget.TextView star = new android.widget.TextView(this);
        star.setText("✦");
        star.setTextSize(36f);
        star.setTextColor(Color.WHITE);
        star.setGravity(Gravity.CENTER);
        star.setLayoutParams(new android.widget.FrameLayout.LayoutParams(
            android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
            android.widget.FrameLayout.LayoutParams.MATCH_PARENT
        ));
        frame.addView(star);

        // Elevação (sombra)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            frame.setElevation(12f);
        }

        return frame;
    }

    // ── Touch: arraste + tap ───────────────────────────────────────────────────

    private boolean onTouch(View v, MotionEvent event) {
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                initialX      = params.x;
                initialY      = params.y;
                initialTouchX = event.getRawX();
                initialTouchY = event.getRawY();
                touchDownTime = System.currentTimeMillis();
                return true;

            case MotionEvent.ACTION_MOVE:
                params.x = initialX + (int)(event.getRawX() - initialTouchX);
                params.y = initialY + (int)(event.getRawY() - initialTouchY);
                windowManager.updateViewLayout(bubbleView, params);
                return true;

            case MotionEvent.ACTION_UP:
                float dx = Math.abs(event.getRawX() - initialTouchX);
                float dy = Math.abs(event.getRawY() - initialTouchY);
                long dt = System.currentTimeMillis() - touchDownTime;
                boolean ehTap = dx < 15 && dy < 15 && dt < 300;
                if (ehTap) {
                    abrirApp();
                } else {
                    grudarNaBorda();
                }
                return true;
        }
        return false;
    }

    /** Gruda a bolha na borda esquerda ou direita mais próxima. */
    private void grudarNaBorda() {
        android.util.DisplayMetrics dm = new android.util.DisplayMetrics();
        windowManager.getDefaultDisplay().getMetrics(dm);
        int metade = dm.widthPixels / 2;
        int alvo   = params.x + BUBBLE_SIZE / 2 < metade ? 0 : dm.widthPixels - BUBBLE_SIZE;

        // Animação simples sem ObjectAnimator para evitar dependências extras
        final int inicio = params.x;
        final int fim    = alvo;
        final long duracao = 200L;
        final long start   = System.currentTimeMillis();

        new Thread(() -> {
            while (true) {
                long elapsed = System.currentTimeMillis() - start;
                float t = Math.min(1f, (float) elapsed / duracao);
                // ease out cubic
                float ease = 1f - (1f - t) * (1f - t) * (1f - t);
                params.x = inicio + (int)((fim - inicio) * ease);
                try {
                    runOnUiThread(() -> {
                        try { windowManager.updateViewLayout(bubbleView, params); }
                        catch (Exception ignored) {}
                    });
                } catch (Exception ignored) {}
                if (t >= 1f) break;
                try { Thread.sleep(16); } catch (InterruptedException ignored) { break; }
            }
        }).start();
    }

    /** Abre o app principal (PythonActivity). */
    private void abrirApp() {
        Intent intent = new Intent(this, getMainActivityClass());
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(intent);
    }

    @SuppressWarnings("unchecked")
    private Class<?> getMainActivityClass() {
        try {
            return Class.forName("org.kivy.android.PythonActivity");
        } catch (ClassNotFoundException e) {
            return getClass();
        }
    }

    /** Utilitário para rodar na UI thread. */
    private void runOnUiThread(Runnable r) {
        android.os.Handler handler = new android.os.Handler(android.os.Looper.getMainLooper());
        handler.post(r);
    }
}
