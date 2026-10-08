class SettlementActionPolicy {
  const SettlementActionPolicy._();

  static bool canClaimPaid(String status, bool isPayer) =>
      isPayer && status == 'PENDING';
  static bool canConfirmOrReject(String status, bool isPayer) =>
      !isPayer && status == 'PAYMENT_CLAIMED';
  static bool canCancel(String status, bool isPayer) =>
      !isPayer && status == 'PENDING';
}
