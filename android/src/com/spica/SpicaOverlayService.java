package com.spica;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

public class SpicaOverlayService extends Service {

    private static final String CHANNEL_ID  = "spica_overlay";
    private static final int    NOTIF_ID    = 1001;
    private static final int    BUBBLE_SIZE = 160;

    private WindowManager windowManager;
    private View          bubbleView;
    private WindowManager.LayoutParams params;
    private Handler mainHandler;

    private int   initialX, initialY;
    private float initialTouchX, initialTouchY;
    private long  touchDownTime;

    @Override
    public void onCreate() {
        super.onCreate();
        mainHandler = new Handler(Looper.getMainLooper());
        // CRÍTICO: chamar startForeground IMEDIATAMENTE no onCreate
        // antes de qualquer outra coisa para evitar ForegroundServiceDidNotStartInTimeException
        criarNotificacao();
        // Criar bolha logo após (ainda no onCreate)
        mainHandler.post(this::criarBolha);
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

    // ── Notificação — startForeground IMEDIATO ────────────────────────────────

    private void criarNotificacao() {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel canal = new NotificationChannel(
                CHANNEL_ID, "Spica",
                NotificationManager.IMPORTANCE_MIN
            );
            canal.setShowBadge(false);
            canal.setSound(null, null);
            if (nm != null) nm.createNotificationChannel(canal);
        }

        Intent abrirApp = new Intent(this, getMainActivityClass());
        abrirApp.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        int piFlags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
            ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            : PendingIntent.FLAG_UPDATE_CURRENT;
        PendingIntent pi = PendingIntent.getActivity(this, 0, abrirApp, piFlags);

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
            builder.setPriority(Notification.PRIORITY_MIN);
        }

        builder.setContentTitle("Spica")
               .setContentText("Assistente ativa")
               .setSmallIcon(android.R.drawable.ic_dialog_info)
               .setOngoing(true)
               .setContentIntent(pi);

        // CRÍTICO: startForeground imediatamente
        startForeground(NOTIF_ID, builder.build());
    }

    // ── Bolha flutuante ───────────────────────────────────────────────────────

    private void criarBolha() {
        try {
            windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

            int tipo = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;  // Android < 8

            params = new WindowManager.LayoutParams(
                BUBBLE_SIZE, BUBBLE_SIZE,
                tipo,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                    | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT
            );
            params.gravity = Gravity.TOP | Gravity.START;
            params.x = 0;
            params.y = 400;

            bubbleView = criarViewBolha();
            bubbleView.setOnTouchListener(this::onTouch);
            windowManager.addView(bubbleView, params);
            System.out.println("[Spica] Bolha adicionada ao WindowManager");
        } catch (Exception e) {
            System.out.println("[Spica] criarBolha erro: " + e.getMessage());
        }
    }

    // ── Visual — substitua aqui pelo PNG V-Tuber ──────────────────────────────

    private View criarViewBolha() {
        FrameLayout frame = new FrameLayout(this);
        frame.setLayoutParams(new FrameLayout.LayoutParams(BUBBLE_SIZE, BUBBLE_SIZE));

        GradientDrawable circle = new GradientDrawable();
        circle.setShape(GradientDrawable.OVAL);
        circle.setColor(Color.parseColor("#1A3A6B"));
        circle.setStroke(5, Color.parseColor("#4A9EFF"));
        frame.setBackground(circle);

        TextView star = new TextView(this);
        star.setText("\u2736");
        star.setTextSize(34f);
        star.setTextColor(Color.parseColor("#4A9EFF"));
        star.setGravity(Gravity.CENTER);
        star.setLayoutParams(new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        ));
        frame.addView(star);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            frame.setElevation(12f);
        }
        return frame;
    }

    // ── Touch ─────────────────────────────────────────────────────────────────

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
                try { windowManager.updateViewLayout(bubbleView, params); }
                catch (Exception ignored) {}
                return true;

            case MotionEvent.ACTION_UP:
                float dx = Math.abs(event.getRawX() - initialTouchX);
                float dy = Math.abs(event.getRawY() - initialTouchY);
                long  dt = System.currentTimeMillis() - touchDownTime;
                if (dx < 20 && dy < 20 && dt < 350) {
                    abrirApp();
                } else {
                    grudarNaBorda();
                }
                return true;
        }
        return false;
    }

    private void grudarNaBorda() {
        android.util.DisplayMetrics dm = new android.util.DisplayMetrics();
        windowManager.getDefaultDisplay().getMetrics(dm);
        final int inicio = params.x;
        final int fim    = (params.x + BUBBLE_SIZE / 2 < dm.widthPixels / 2)
                           ? 0 : dm.widthPixels - BUBBLE_SIZE;
        final long duracao = 180L;
        final long start   = System.currentTimeMillis();
        Runnable anim = new Runnable() {
            @Override public void run() {
                float t    = Math.min(1f, (float)(System.currentTimeMillis() - start) / duracao);
                float ease = 1f - (1f - t) * (1f - t) * (1f - t);
                params.x   = inicio + (int)((fim - inicio) * ease);
                try { windowManager.updateViewLayout(bubbleView, params); }
                catch (Exception ignored) {}
                if (t < 1f) mainHandler.postDelayed(this, 16);
            }
        };
        mainHandler.post(anim);
    }

    private void abrirApp() {
        try {
            Intent intent = new Intent(this, getMainActivityClass());
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(intent);
        } catch (Exception e) {
            System.out.println("[Spica] abrirApp erro: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Class<?> getMainActivityClass() {
        try { return Class.forName("org.kivy.android.PythonActivity"); }
        catch (ClassNotFoundException e) { return getClass(); }
    }
}
