import React, { useState } from "react";
import { Bell, X, Check, Mail, Webhook, ShieldAlert, Sparkles } from "lucide-react";

interface AlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  referenceImage?: string;
  onSaveAlert: (alertConfig: { email: string; webhookUrl: string; notifyOnNewAppearance: boolean }) => void;
}

export const AlertModal: React.FC<AlertModalProps> = ({
  isOpen,
  onClose,
  referenceImage,
  onSaveAlert,
}) => {
  const [email, setEmail] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [notifyOnNewAppearance, setNotifyOnNewAppearance] = useState(true);
  const [isSubmitted, setIsSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveAlert({ email, webhookUrl, notifyOnNewAppearance });
    setIsSubmitted(true);
    setTimeout(() => {
      setIsSubmitted(false);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 max-w-md w-full p-6 relative animate-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Visual Exposure Alert</h3>
            <p className="text-xs text-slate-500">
              Get notified whenever this image appears online
            </p>
          </div>
        </div>

        {referenceImage && (
          <div className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200/60 rounded-xl mb-4">
            <img
              src={referenceImage}
              alt="Tracked reference"
              className="w-12 h-12 object-cover rounded-lg border border-slate-200"
            />
            <div className="text-xs">
              <span className="font-semibold text-slate-800">Tracking Active Image Fingerprint</span>
              <p className="text-slate-500">Monitored across web discovery streams</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Email Notification
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@cyberhub.security"
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-800"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Webhook URL (Optional)
            </label>
            <div className="relative">
              <Webhook className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-800"
              />
            </div>
          </div>

          <label className="flex items-center gap-2.5 p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/50 cursor-pointer">
            <input
              type="checkbox"
              checked={notifyOnNewAppearance}
              onChange={(e) => setNotifyOnNewAppearance(e.target.checked)}
              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-xs font-medium text-slate-700">
              Immediate alert on high-confidence visual & facial matches
            </span>
          </label>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitted}
              className="px-5 py-2 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow flex items-center gap-2 transition"
            >
              {isSubmitted ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" /> Alert Created!
                </>
              ) : (
                <>
                  <Bell className="w-4 h-4" /> Create Alert
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
