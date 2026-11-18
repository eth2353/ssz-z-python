//! Generated from ethereum/consensus-specs v1.7.0-beta.4 (aa16bb4c156184e9548a997d53efaf2a228a6304).
//! Regenerate with tools/generate_schemas.py. The engine is Lodestar-Z SSZ.
const std = @import("std");
const ssz = @import("ssz");
const constants = @import("constants");
const preset_module = @import("preset");
const preset = preset_module.preset;
pub const primitive = @import("primitive");
pub const electra = struct {
    pub const Bytes4 = ssz.ByteVectorType(4);
    pub const Version = Bytes4;
    pub const Uint64 = ssz.UintType(64);
    pub const Epoch = Uint64;
    pub const Fork = ssz.FixedContainerType(struct {
        previous_version: Version,
        current_version: Version,
        epoch: Epoch,
    });
    pub const Bytes32 = ssz.ByteVectorType(32);
    pub const Root = Bytes32;
    pub const ForkData = ssz.FixedContainerType(struct {
        current_version: Version,
        genesis_validators_root: Root,
    });
    pub const Checkpoint = ssz.FixedContainerType(struct {
        epoch: Epoch,
        root: Root,
    });
    pub const Bytes48 = ssz.ByteVectorType(48);
    pub const BLSPubkey = Bytes48;
    pub const Gwei = Uint64;
    pub const Boolean = ssz.BoolType();
    pub const Validator = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        effective_balance: Gwei,
        slashed: Boolean,
        activation_eligibility_epoch: Epoch,
        activation_epoch: Epoch,
        exit_epoch: Epoch,
        withdrawable_epoch: Epoch,
    });
    pub const Slot = Uint64;
    pub const CommitteeIndex = Uint64;
    pub const AttestationData = ssz.FixedContainerType(struct {
        slot: Slot,
        index: CommitteeIndex,
        beacon_block_root: Root,
        source: Checkpoint,
        target: Checkpoint,
    });
    pub const ValidatorIndex = Uint64;
    pub const AttestingIndices = ssz.FixedListType(ValidatorIndex, (preset.MAX_VALIDATORS_PER_COMMITTEE * preset.MAX_COMMITTEES_PER_SLOT), .{});
    pub const Bytes96 = ssz.ByteVectorType(96);
    pub const BLSSignature = Bytes96;
    pub const IndexedAttestation = ssz.VariableContainerType(struct {
        attesting_indices: AttestingIndices,
        data: AttestationData,
        signature: BLSSignature,
    });
    pub const AggregationBits = ssz.BitListType((preset.MAX_VALIDATORS_PER_COMMITTEE * preset.MAX_COMMITTEES_PER_SLOT));
    pub const PendingAttestation = ssz.VariableContainerType(struct {
        aggregation_bits: AggregationBits,
        data: AttestationData,
        inclusion_delay: Slot,
        proposer_index: ValidatorIndex,
    });
    pub const Hash32 = Bytes32;
    pub const Eth1Data = ssz.FixedContainerType(struct {
        deposit_root: Root,
        deposit_count: Uint64,
        block_hash: Hash32,
    });
    pub const BlockRoots = ssz.FixedVectorType(Root, preset.SLOTS_PER_HISTORICAL_ROOT, .{});
    pub const StateRoots = ssz.FixedVectorType(Root, preset.SLOTS_PER_HISTORICAL_ROOT, .{});
    pub const HistoricalBatch = ssz.FixedContainerType(struct {
        block_roots: BlockRoots,
        state_roots: StateRoots,
    });
    pub const DepositMessage = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
    });
    pub const DepositData = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
    });
    pub const BeaconBlockHeader = ssz.FixedContainerType(struct {
        slot: Slot,
        proposer_index: ValidatorIndex,
        parent_root: Root,
        state_root: Root,
        body_root: Root,
    });
    pub const Domain = Bytes32;
    pub const SigningData = ssz.FixedContainerType(struct {
        object_root: Root,
        domain: Domain,
    });
    pub const SignedBeaconBlockHeader = ssz.FixedContainerType(struct {
        message: BeaconBlockHeader,
        signature: BLSSignature,
    });
    pub const ProposerSlashing = ssz.FixedContainerType(struct {
        signed_header_1: SignedBeaconBlockHeader,
        signed_header_2: SignedBeaconBlockHeader,
    });
    pub const AttesterSlashing = ssz.VariableContainerType(struct {
        attestation_1: IndexedAttestation,
        attestation_2: IndexedAttestation,
    });
    pub const CommitteeBits = ssz.BitVectorType(preset.MAX_COMMITTEES_PER_SLOT);
    pub const Attestation = ssz.VariableContainerType(struct {
        aggregation_bits: AggregationBits,
        data: AttestationData,
        signature: BLSSignature,
        committee_bits: CommitteeBits,
    });
    pub const DepositProof = ssz.FixedVectorType(Bytes32, (constants.DEPOSIT_CONTRACT_TREE_DEPTH + 1), .{});
    pub const Deposit = ssz.FixedContainerType(struct {
        proof: DepositProof,
        data: DepositData,
    });
    pub const VoluntaryExit = ssz.FixedContainerType(struct {
        epoch: Epoch,
        validator_index: ValidatorIndex,
    });
    pub const ProposerSlashings = ssz.FixedListType(ProposerSlashing, preset.MAX_PROPOSER_SLASHINGS, .{});
    pub const AttesterSlashings = ssz.VariableListType(AttesterSlashing, preset.MAX_ATTESTER_SLASHINGS_ELECTRA);
    pub const Attestations = ssz.VariableListType(Attestation, preset.MAX_ATTESTATIONS_ELECTRA);
    pub const Deposits = ssz.FixedListType(Deposit, preset.MAX_DEPOSITS, .{});
    pub const SignedVoluntaryExit = ssz.FixedContainerType(struct {
        message: VoluntaryExit,
        signature: BLSSignature,
    });
    pub const VoluntaryExits = ssz.FixedListType(SignedVoluntaryExit, preset.MAX_VOLUNTARY_EXITS, .{});
    pub const SyncCommitteeBits = ssz.BitVectorType(preset.SYNC_COMMITTEE_SIZE);
    pub const SyncAggregate = ssz.FixedContainerType(struct {
        sync_committee_bits: SyncCommitteeBits,
        sync_committee_signature: BLSSignature,
    });
    pub const Bytes20 = ssz.ByteVectorType(20);
    pub const ExecutionAddress = Bytes20;
    pub const LogsBloom = ssz.ByteVectorType(preset.BYTES_PER_LOGS_BLOOM);
    pub const ExtraData = ssz.ByteListType(preset.MAX_EXTRA_DATA_BYTES);
    pub const Uint256 = ssz.UintType(256);
    pub const Transaction = ssz.ByteListType(preset.MAX_BYTES_PER_TRANSACTION);
    pub const Transactions = ssz.VariableListType(Transaction, preset.MAX_TRANSACTIONS_PER_PAYLOAD);
    pub const WithdrawalIndex = Uint64;
    pub const Withdrawal = ssz.FixedContainerType(struct {
        index: WithdrawalIndex,
        validator_index: ValidatorIndex,
        address: ExecutionAddress,
        amount: Gwei,
    });
    pub const Withdrawals = ssz.FixedListType(Withdrawal, preset.MAX_WITHDRAWALS_PER_PAYLOAD, .{});
    pub const ExecutionPayload = ssz.VariableContainerType(struct {
        parent_hash: Hash32,
        fee_recipient: ExecutionAddress,
        state_root: Bytes32,
        receipts_root: Bytes32,
        logs_bloom: LogsBloom,
        prev_randao: Bytes32,
        block_number: Uint64,
        gas_limit: Uint64,
        gas_used: Uint64,
        timestamp: Uint64,
        extra_data: ExtraData,
        base_fee_per_gas: Uint256,
        block_hash: Hash32,
        transactions: Transactions,
        withdrawals: Withdrawals,
        blob_gas_used: Uint64,
        excess_blob_gas: Uint64,
    });
    pub const BLSToExecutionChange = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        from_bls_pubkey: BLSPubkey,
        to_execution_address: ExecutionAddress,
    });
    pub const SignedBLSToExecutionChange = ssz.FixedContainerType(struct {
        message: BLSToExecutionChange,
        signature: BLSSignature,
    });
    pub const BLSToExecutionChanges = ssz.FixedListType(SignedBLSToExecutionChange, preset.MAX_BLS_TO_EXECUTION_CHANGES, .{});
    pub const KZGCommitment = Bytes48;
    pub const BlobKZGCommitments = ssz.FixedListType(KZGCommitment, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const DepositRequest = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
        index: Uint64,
    });
    pub const DepositRequests = ssz.FixedListType(DepositRequest, preset.MAX_DEPOSIT_REQUESTS_PER_PAYLOAD, .{});
    pub const WithdrawalRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        validator_pubkey: BLSPubkey,
        amount: Gwei,
    });
    pub const WithdrawalRequests = ssz.FixedListType(WithdrawalRequest, preset.MAX_WITHDRAWAL_REQUESTS_PER_PAYLOAD, .{});
    pub const ConsolidationRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        source_pubkey: BLSPubkey,
        target_pubkey: BLSPubkey,
    });
    pub const ConsolidationRequests = ssz.FixedListType(ConsolidationRequest, preset.MAX_CONSOLIDATION_REQUESTS_PER_PAYLOAD, .{});
    pub const ExecutionRequests = ssz.VariableContainerType(struct {
        deposits: DepositRequests,
        withdrawals: WithdrawalRequests,
        consolidations: ConsolidationRequests,
    });
    pub const BeaconBlockBody = ssz.VariableContainerType(struct {
        randao_reveal: BLSSignature,
        eth1_data: Eth1Data,
        graffiti: Bytes32,
        proposer_slashings: ProposerSlashings,
        attester_slashings: AttesterSlashings,
        attestations: Attestations,
        deposits: Deposits,
        voluntary_exits: VoluntaryExits,
        sync_aggregate: SyncAggregate,
        execution_payload: ExecutionPayload,
        bls_to_execution_changes: BLSToExecutionChanges,
        blob_kzg_commitments: BlobKZGCommitments,
        execution_requests: ExecutionRequests,
    });
    pub const BeaconBlock = ssz.VariableContainerType(struct {
        slot: Slot,
        proposer_index: ValidatorIndex,
        parent_root: Root,
        state_root: Root,
        body: BeaconBlockBody,
    });
    pub const HistoricalRoots = ssz.FixedListType(Root, preset.HISTORICAL_ROOTS_LIMIT, .{});
    pub const Eth1DataVotes = ssz.FixedListType(Eth1Data, (preset.EPOCHS_PER_ETH1_VOTING_PERIOD * preset.SLOTS_PER_EPOCH), .{});
    pub const Validators = ssz.FixedListType(Validator, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const Balances = ssz.FixedListType(Gwei, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const RandaoMixes = ssz.FixedVectorType(Bytes32, preset.EPOCHS_PER_HISTORICAL_VECTOR, .{});
    pub const Slashings = ssz.FixedVectorType(Gwei, preset.EPOCHS_PER_SLASHINGS_VECTOR, .{});
    pub const Uint8 = ssz.UintType(8);
    pub const ParticipationFlags = Uint8;
    pub const EpochParticipation = ssz.FixedListType(ParticipationFlags, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const JustificationBits = ssz.BitVectorType(constants.JUSTIFICATION_BITS_LENGTH);
    pub const InactivityScores = ssz.FixedListType(Uint64, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const SyncCommitteePubkeys = ssz.FixedVectorType(BLSPubkey, preset.SYNC_COMMITTEE_SIZE, .{});
    pub const SyncCommittee = ssz.FixedContainerType(struct {
        pubkeys: SyncCommitteePubkeys,
        aggregate_pubkey: BLSPubkey,
    });
    pub const ExecutionPayloadHeader = ssz.VariableContainerType(struct {
        parent_hash: Hash32,
        fee_recipient: ExecutionAddress,
        state_root: Bytes32,
        receipts_root: Bytes32,
        logs_bloom: LogsBloom,
        prev_randao: Bytes32,
        block_number: Uint64,
        gas_limit: Uint64,
        gas_used: Uint64,
        timestamp: Uint64,
        extra_data: ExtraData,
        base_fee_per_gas: Uint256,
        block_hash: Hash32,
        transactions_root: Root,
        withdrawals_root: Root,
        blob_gas_used: Uint64,
        excess_blob_gas: Uint64,
    });
    pub const HistoricalSummary = ssz.FixedContainerType(struct {
        block_summary_root: Root,
        state_summary_root: Root,
    });
    pub const HistoricalSummaries = ssz.FixedListType(HistoricalSummary, preset.HISTORICAL_ROOTS_LIMIT, .{});
    pub const PendingDeposit = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
        slot: Slot,
    });
    pub const PendingDeposits = ssz.FixedListType(PendingDeposit, preset.PENDING_DEPOSITS_LIMIT, .{});
    pub const PendingPartialWithdrawal = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        amount: Gwei,
        withdrawable_epoch: Epoch,
    });
    pub const PendingPartialWithdrawals = ssz.FixedListType(PendingPartialWithdrawal, preset.PENDING_PARTIAL_WITHDRAWALS_LIMIT, .{});
    pub const PendingConsolidation = ssz.FixedContainerType(struct {
        source_index: ValidatorIndex,
        target_index: ValidatorIndex,
    });
    pub const PendingConsolidations = ssz.FixedListType(PendingConsolidation, preset.PENDING_CONSOLIDATIONS_LIMIT, .{});
    pub const BeaconState = ssz.VariableContainerType(struct {
        genesis_time: Uint64,
        genesis_validators_root: Root,
        slot: Slot,
        fork: Fork,
        latest_block_header: BeaconBlockHeader,
        block_roots: BlockRoots,
        state_roots: StateRoots,
        historical_roots: HistoricalRoots,
        eth1_data: Eth1Data,
        eth1_data_votes: Eth1DataVotes,
        eth1_deposit_index: Uint64,
        validators: Validators,
        balances: Balances,
        randao_mixes: RandaoMixes,
        slashings: Slashings,
        previous_epoch_participation: EpochParticipation,
        current_epoch_participation: EpochParticipation,
        justification_bits: JustificationBits,
        previous_justified_checkpoint: Checkpoint,
        current_justified_checkpoint: Checkpoint,
        finalized_checkpoint: Checkpoint,
        inactivity_scores: InactivityScores,
        current_sync_committee: SyncCommittee,
        next_sync_committee: SyncCommittee,
        latest_execution_payload_header: ExecutionPayloadHeader,
        next_withdrawal_index: WithdrawalIndex,
        next_withdrawal_validator_index: ValidatorIndex,
        historical_summaries: HistoricalSummaries,
        deposit_requests_start_index: Uint64,
        deposit_balance_to_consume: Gwei,
        exit_balance_to_consume: Gwei,
        earliest_exit_epoch: Epoch,
        consolidation_balance_to_consume: Gwei,
        earliest_consolidation_epoch: Epoch,
        pending_deposits: PendingDeposits,
        pending_partial_withdrawals: PendingPartialWithdrawals,
        pending_consolidations: PendingConsolidations,
    });
    pub const SignedBeaconBlock = ssz.VariableContainerType(struct {
        message: BeaconBlock,
        signature: BLSSignature,
    });
    pub const Eth1Block = ssz.FixedContainerType(struct {
        timestamp: Uint64,
        deposit_root: Root,
        deposit_count: Uint64,
    });
    pub const AggregateAndProof = ssz.VariableContainerType(struct {
        aggregator_index: ValidatorIndex,
        aggregate: Attestation,
        selection_proof: BLSSignature,
    });
    pub const SignedAggregateAndProof = ssz.VariableContainerType(struct {
        message: AggregateAndProof,
        signature: BLSSignature,
    });
    pub const ExecutionBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.EXECUTION_PAYLOAD_GINDEX), .{});
    pub const LightClientHeader = ssz.VariableContainerType(struct {
        beacon: BeaconBlockHeader,
        execution: ExecutionPayloadHeader,
        execution_branch: ExecutionBranch,
    });
    pub const CurrentSyncCommitteeBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.CURRENT_SYNC_COMMITTEE_GINDEX_ELECTRA), .{});
    pub const LightClientBootstrap = ssz.VariableContainerType(struct {
        header: LightClientHeader,
        current_sync_committee: SyncCommittee,
        current_sync_committee_branch: CurrentSyncCommitteeBranch,
    });
    pub const NextSyncCommitteeBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.NEXT_SYNC_COMMITTEE_GINDEX_ELECTRA), .{});
    pub const FinalityBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.FINALIZED_ROOT_GINDEX_ELECTRA), .{});
    pub const LightClientUpdate = ssz.VariableContainerType(struct {
        attested_header: LightClientHeader,
        next_sync_committee: SyncCommittee,
        next_sync_committee_branch: NextSyncCommitteeBranch,
        finalized_header: LightClientHeader,
        finality_branch: FinalityBranch,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const LightClientFinalityUpdate = ssz.VariableContainerType(struct {
        attested_header: LightClientHeader,
        finalized_header: LightClientHeader,
        finality_branch: FinalityBranch,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const LightClientOptimisticUpdate = ssz.VariableContainerType(struct {
        attested_header: LightClientHeader,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const SyncCommitteeMessage = ssz.FixedContainerType(struct {
        slot: Slot,
        beacon_block_root: Root,
        validator_index: ValidatorIndex,
        signature: BLSSignature,
    });
    pub const SyncSubcommitteeBits = ssz.BitVectorType(@divFloor(preset.SYNC_COMMITTEE_SIZE, constants.SYNC_COMMITTEE_SUBNET_COUNT));
    pub const SyncCommitteeContribution = ssz.FixedContainerType(struct {
        slot: Slot,
        beacon_block_root: Root,
        subcommittee_index: Uint64,
        aggregation_bits: SyncSubcommitteeBits,
        signature: BLSSignature,
    });
    pub const ContributionAndProof = ssz.FixedContainerType(struct {
        aggregator_index: ValidatorIndex,
        contribution: SyncCommitteeContribution,
        selection_proof: BLSSignature,
    });
    pub const SignedContributionAndProof = ssz.FixedContainerType(struct {
        message: ContributionAndProof,
        signature: BLSSignature,
    });
    pub const SyncAggregatorSelectionData = ssz.FixedContainerType(struct {
        slot: Slot,
        subcommittee_index: Uint64,
    });
    pub const VersionedHash = Bytes32;
    pub const VersionedHashes = ssz.FixedListType(VersionedHash, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const NewPayloadRequest = ssz.VariableContainerType(struct {
        execution_payload: ExecutionPayload,
        versioned_hashes: VersionedHashes,
        parent_beacon_block_root: Root,
        execution_requests: ExecutionRequests,
    });
    pub const PowBlock = ssz.FixedContainerType(struct {
        block_hash: Hash32,
        parent_hash: Hash32,
        total_difficulty: Uint256,
    });
    pub const BlobIndex = Uint64;
    pub const Blob = ssz.ByteVectorType((constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_BLOB));
    pub const KZGProof = Bytes48;
    pub const KZGCommitmentInclusionProof = ssz.FixedVectorType(Bytes32, preset.KZG_COMMITMENT_INCLUSION_PROOF_DEPTH, .{});
    pub const BlobSidecar = ssz.FixedContainerType(struct {
        index: BlobIndex,
        blob: Blob,
        kzg_commitment: KZGCommitment,
        kzg_proof: KZGProof,
        signed_block_header: SignedBeaconBlockHeader,
        kzg_commitment_inclusion_proof: KZGCommitmentInclusionProof,
    });
    pub const BlobIdentifier = ssz.FixedContainerType(struct {
        block_root: Root,
        index: BlobIndex,
    });
    pub const SingleAttestation = ssz.FixedContainerType(struct {
        committee_index: CommitteeIndex,
        attester_index: ValidatorIndex,
        data: AttestationData,
        signature: BLSSignature,
    });
    const api = @import("beacon_api.zig").Types(@This(), false);
    pub const BeaconBlockContents = api.BeaconBlockContents;
    pub const SignedBeaconBlockContents = api.SignedBeaconBlockContents;
    pub const BlindedBeaconBlockBody = api.BlindedBeaconBlockBody;
    pub const BlindedBeaconBlock = api.BlindedBeaconBlock;
    pub const SignedBlindedBeaconBlock = api.SignedBlindedBeaconBlock;
};
pub const fulu = struct {
    pub const Bytes4 = ssz.ByteVectorType(4);
    pub const Version = Bytes4;
    pub const Uint64 = ssz.UintType(64);
    pub const Epoch = Uint64;
    pub const Fork = ssz.FixedContainerType(struct {
        previous_version: Version,
        current_version: Version,
        epoch: Epoch,
    });
    pub const Bytes32 = ssz.ByteVectorType(32);
    pub const Root = Bytes32;
    pub const ForkData = ssz.FixedContainerType(struct {
        current_version: Version,
        genesis_validators_root: Root,
    });
    pub const Checkpoint = ssz.FixedContainerType(struct {
        epoch: Epoch,
        root: Root,
    });
    pub const Bytes48 = ssz.ByteVectorType(48);
    pub const BLSPubkey = Bytes48;
    pub const Gwei = Uint64;
    pub const Boolean = ssz.BoolType();
    pub const Validator = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        effective_balance: Gwei,
        slashed: Boolean,
        activation_eligibility_epoch: Epoch,
        activation_epoch: Epoch,
        exit_epoch: Epoch,
        withdrawable_epoch: Epoch,
    });
    pub const Slot = Uint64;
    pub const CommitteeIndex = Uint64;
    pub const AttestationData = ssz.FixedContainerType(struct {
        slot: Slot,
        index: CommitteeIndex,
        beacon_block_root: Root,
        source: Checkpoint,
        target: Checkpoint,
    });
    pub const ValidatorIndex = Uint64;
    pub const AttestingIndices = ssz.FixedListType(ValidatorIndex, (preset.MAX_VALIDATORS_PER_COMMITTEE * preset.MAX_COMMITTEES_PER_SLOT), .{});
    pub const Bytes96 = ssz.ByteVectorType(96);
    pub const BLSSignature = Bytes96;
    pub const IndexedAttestation = ssz.VariableContainerType(struct {
        attesting_indices: AttestingIndices,
        data: AttestationData,
        signature: BLSSignature,
    });
    pub const AggregationBits = ssz.BitListType((preset.MAX_VALIDATORS_PER_COMMITTEE * preset.MAX_COMMITTEES_PER_SLOT));
    pub const PendingAttestation = ssz.VariableContainerType(struct {
        aggregation_bits: AggregationBits,
        data: AttestationData,
        inclusion_delay: Slot,
        proposer_index: ValidatorIndex,
    });
    pub const Hash32 = Bytes32;
    pub const Eth1Data = ssz.FixedContainerType(struct {
        deposit_root: Root,
        deposit_count: Uint64,
        block_hash: Hash32,
    });
    pub const BlockRoots = ssz.FixedVectorType(Root, preset.SLOTS_PER_HISTORICAL_ROOT, .{});
    pub const StateRoots = ssz.FixedVectorType(Root, preset.SLOTS_PER_HISTORICAL_ROOT, .{});
    pub const HistoricalBatch = ssz.FixedContainerType(struct {
        block_roots: BlockRoots,
        state_roots: StateRoots,
    });
    pub const DepositMessage = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
    });
    pub const DepositData = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
    });
    pub const BeaconBlockHeader = ssz.FixedContainerType(struct {
        slot: Slot,
        proposer_index: ValidatorIndex,
        parent_root: Root,
        state_root: Root,
        body_root: Root,
    });
    pub const Domain = Bytes32;
    pub const SigningData = ssz.FixedContainerType(struct {
        object_root: Root,
        domain: Domain,
    });
    pub const SignedBeaconBlockHeader = ssz.FixedContainerType(struct {
        message: BeaconBlockHeader,
        signature: BLSSignature,
    });
    pub const ProposerSlashing = ssz.FixedContainerType(struct {
        signed_header_1: SignedBeaconBlockHeader,
        signed_header_2: SignedBeaconBlockHeader,
    });
    pub const AttesterSlashing = ssz.VariableContainerType(struct {
        attestation_1: IndexedAttestation,
        attestation_2: IndexedAttestation,
    });
    pub const CommitteeBits = ssz.BitVectorType(preset.MAX_COMMITTEES_PER_SLOT);
    pub const Attestation = ssz.VariableContainerType(struct {
        aggregation_bits: AggregationBits,
        data: AttestationData,
        signature: BLSSignature,
        committee_bits: CommitteeBits,
    });
    pub const DepositProof = ssz.FixedVectorType(Bytes32, (constants.DEPOSIT_CONTRACT_TREE_DEPTH + 1), .{});
    pub const Deposit = ssz.FixedContainerType(struct {
        proof: DepositProof,
        data: DepositData,
    });
    pub const VoluntaryExit = ssz.FixedContainerType(struct {
        epoch: Epoch,
        validator_index: ValidatorIndex,
    });
    pub const ProposerSlashings = ssz.FixedListType(ProposerSlashing, preset.MAX_PROPOSER_SLASHINGS, .{});
    pub const AttesterSlashings = ssz.VariableListType(AttesterSlashing, preset.MAX_ATTESTER_SLASHINGS_ELECTRA);
    pub const Attestations = ssz.VariableListType(Attestation, preset.MAX_ATTESTATIONS_ELECTRA);
    pub const Deposits = ssz.FixedListType(Deposit, preset.MAX_DEPOSITS, .{});
    pub const SignedVoluntaryExit = ssz.FixedContainerType(struct {
        message: VoluntaryExit,
        signature: BLSSignature,
    });
    pub const VoluntaryExits = ssz.FixedListType(SignedVoluntaryExit, preset.MAX_VOLUNTARY_EXITS, .{});
    pub const SyncCommitteeBits = ssz.BitVectorType(preset.SYNC_COMMITTEE_SIZE);
    pub const SyncAggregate = ssz.FixedContainerType(struct {
        sync_committee_bits: SyncCommitteeBits,
        sync_committee_signature: BLSSignature,
    });
    pub const Bytes20 = ssz.ByteVectorType(20);
    pub const ExecutionAddress = Bytes20;
    pub const LogsBloom = ssz.ByteVectorType(preset.BYTES_PER_LOGS_BLOOM);
    pub const ExtraData = ssz.ByteListType(preset.MAX_EXTRA_DATA_BYTES);
    pub const Uint256 = ssz.UintType(256);
    pub const Transaction = ssz.ByteListType(preset.MAX_BYTES_PER_TRANSACTION);
    pub const Transactions = ssz.VariableListType(Transaction, preset.MAX_TRANSACTIONS_PER_PAYLOAD);
    pub const WithdrawalIndex = Uint64;
    pub const Withdrawal = ssz.FixedContainerType(struct {
        index: WithdrawalIndex,
        validator_index: ValidatorIndex,
        address: ExecutionAddress,
        amount: Gwei,
    });
    pub const Withdrawals = ssz.FixedListType(Withdrawal, preset.MAX_WITHDRAWALS_PER_PAYLOAD, .{});
    pub const ExecutionPayload = ssz.VariableContainerType(struct {
        parent_hash: Hash32,
        fee_recipient: ExecutionAddress,
        state_root: Bytes32,
        receipts_root: Bytes32,
        logs_bloom: LogsBloom,
        prev_randao: Bytes32,
        block_number: Uint64,
        gas_limit: Uint64,
        gas_used: Uint64,
        timestamp: Uint64,
        extra_data: ExtraData,
        base_fee_per_gas: Uint256,
        block_hash: Hash32,
        transactions: Transactions,
        withdrawals: Withdrawals,
        blob_gas_used: Uint64,
        excess_blob_gas: Uint64,
    });
    pub const BLSToExecutionChange = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        from_bls_pubkey: BLSPubkey,
        to_execution_address: ExecutionAddress,
    });
    pub const SignedBLSToExecutionChange = ssz.FixedContainerType(struct {
        message: BLSToExecutionChange,
        signature: BLSSignature,
    });
    pub const BLSToExecutionChanges = ssz.FixedListType(SignedBLSToExecutionChange, preset.MAX_BLS_TO_EXECUTION_CHANGES, .{});
    pub const KZGCommitment = Bytes48;
    pub const BlobKZGCommitments = ssz.FixedListType(KZGCommitment, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const DepositRequest = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
        index: Uint64,
    });
    pub const DepositRequests = ssz.FixedListType(DepositRequest, preset.MAX_DEPOSIT_REQUESTS_PER_PAYLOAD, .{});
    pub const WithdrawalRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        validator_pubkey: BLSPubkey,
        amount: Gwei,
    });
    pub const WithdrawalRequests = ssz.FixedListType(WithdrawalRequest, preset.MAX_WITHDRAWAL_REQUESTS_PER_PAYLOAD, .{});
    pub const ConsolidationRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        source_pubkey: BLSPubkey,
        target_pubkey: BLSPubkey,
    });
    pub const ConsolidationRequests = ssz.FixedListType(ConsolidationRequest, preset.MAX_CONSOLIDATION_REQUESTS_PER_PAYLOAD, .{});
    pub const ExecutionRequests = ssz.VariableContainerType(struct {
        deposits: DepositRequests,
        withdrawals: WithdrawalRequests,
        consolidations: ConsolidationRequests,
    });
    pub const BeaconBlockBody = ssz.VariableContainerType(struct {
        randao_reveal: BLSSignature,
        eth1_data: Eth1Data,
        graffiti: Bytes32,
        proposer_slashings: ProposerSlashings,
        attester_slashings: AttesterSlashings,
        attestations: Attestations,
        deposits: Deposits,
        voluntary_exits: VoluntaryExits,
        sync_aggregate: SyncAggregate,
        execution_payload: ExecutionPayload,
        bls_to_execution_changes: BLSToExecutionChanges,
        blob_kzg_commitments: BlobKZGCommitments,
        execution_requests: ExecutionRequests,
    });
    pub const BeaconBlock = ssz.VariableContainerType(struct {
        slot: Slot,
        proposer_index: ValidatorIndex,
        parent_root: Root,
        state_root: Root,
        body: BeaconBlockBody,
    });
    pub const HistoricalRoots = ssz.FixedListType(Root, preset.HISTORICAL_ROOTS_LIMIT, .{});
    pub const Eth1DataVotes = ssz.FixedListType(Eth1Data, (preset.EPOCHS_PER_ETH1_VOTING_PERIOD * preset.SLOTS_PER_EPOCH), .{});
    pub const Validators = ssz.FixedListType(Validator, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const Balances = ssz.FixedListType(Gwei, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const RandaoMixes = ssz.FixedVectorType(Bytes32, preset.EPOCHS_PER_HISTORICAL_VECTOR, .{});
    pub const Slashings = ssz.FixedVectorType(Gwei, preset.EPOCHS_PER_SLASHINGS_VECTOR, .{});
    pub const Uint8 = ssz.UintType(8);
    pub const ParticipationFlags = Uint8;
    pub const EpochParticipation = ssz.FixedListType(ParticipationFlags, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const JustificationBits = ssz.BitVectorType(constants.JUSTIFICATION_BITS_LENGTH);
    pub const InactivityScores = ssz.FixedListType(Uint64, preset.VALIDATOR_REGISTRY_LIMIT, .{});
    pub const SyncCommitteePubkeys = ssz.FixedVectorType(BLSPubkey, preset.SYNC_COMMITTEE_SIZE, .{});
    pub const SyncCommittee = ssz.FixedContainerType(struct {
        pubkeys: SyncCommitteePubkeys,
        aggregate_pubkey: BLSPubkey,
    });
    pub const ExecutionPayloadHeader = ssz.VariableContainerType(struct {
        parent_hash: Hash32,
        fee_recipient: ExecutionAddress,
        state_root: Bytes32,
        receipts_root: Bytes32,
        logs_bloom: LogsBloom,
        prev_randao: Bytes32,
        block_number: Uint64,
        gas_limit: Uint64,
        gas_used: Uint64,
        timestamp: Uint64,
        extra_data: ExtraData,
        base_fee_per_gas: Uint256,
        block_hash: Hash32,
        transactions_root: Root,
        withdrawals_root: Root,
        blob_gas_used: Uint64,
        excess_blob_gas: Uint64,
    });
    pub const HistoricalSummary = ssz.FixedContainerType(struct {
        block_summary_root: Root,
        state_summary_root: Root,
    });
    pub const HistoricalSummaries = ssz.FixedListType(HistoricalSummary, preset.HISTORICAL_ROOTS_LIMIT, .{});
    pub const PendingDeposit = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
        slot: Slot,
    });
    pub const PendingDeposits = ssz.FixedListType(PendingDeposit, preset.PENDING_DEPOSITS_LIMIT, .{});
    pub const PendingPartialWithdrawal = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        amount: Gwei,
        withdrawable_epoch: Epoch,
    });
    pub const PendingPartialWithdrawals = ssz.FixedListType(PendingPartialWithdrawal, preset.PENDING_PARTIAL_WITHDRAWALS_LIMIT, .{});
    pub const PendingConsolidation = ssz.FixedContainerType(struct {
        source_index: ValidatorIndex,
        target_index: ValidatorIndex,
    });
    pub const PendingConsolidations = ssz.FixedListType(PendingConsolidation, preset.PENDING_CONSOLIDATIONS_LIMIT, .{});
    pub const ProposerLookahead = ssz.FixedVectorType(ValidatorIndex, ((preset.MIN_SEED_LOOKAHEAD + 1) * preset.SLOTS_PER_EPOCH), .{});
    pub const BeaconState = ssz.VariableContainerType(struct {
        genesis_time: Uint64,
        genesis_validators_root: Root,
        slot: Slot,
        fork: Fork,
        latest_block_header: BeaconBlockHeader,
        block_roots: BlockRoots,
        state_roots: StateRoots,
        historical_roots: HistoricalRoots,
        eth1_data: Eth1Data,
        eth1_data_votes: Eth1DataVotes,
        eth1_deposit_index: Uint64,
        validators: Validators,
        balances: Balances,
        randao_mixes: RandaoMixes,
        slashings: Slashings,
        previous_epoch_participation: EpochParticipation,
        current_epoch_participation: EpochParticipation,
        justification_bits: JustificationBits,
        previous_justified_checkpoint: Checkpoint,
        current_justified_checkpoint: Checkpoint,
        finalized_checkpoint: Checkpoint,
        inactivity_scores: InactivityScores,
        current_sync_committee: SyncCommittee,
        next_sync_committee: SyncCommittee,
        latest_execution_payload_header: ExecutionPayloadHeader,
        next_withdrawal_index: WithdrawalIndex,
        next_withdrawal_validator_index: ValidatorIndex,
        historical_summaries: HistoricalSummaries,
        deposit_requests_start_index: Uint64,
        deposit_balance_to_consume: Gwei,
        exit_balance_to_consume: Gwei,
        earliest_exit_epoch: Epoch,
        consolidation_balance_to_consume: Gwei,
        earliest_consolidation_epoch: Epoch,
        pending_deposits: PendingDeposits,
        pending_partial_withdrawals: PendingPartialWithdrawals,
        pending_consolidations: PendingConsolidations,
        proposer_lookahead: ProposerLookahead,
    });
    pub const SignedBeaconBlock = ssz.VariableContainerType(struct {
        message: BeaconBlock,
        signature: BLSSignature,
    });
    pub const Eth1Block = ssz.FixedContainerType(struct {
        timestamp: Uint64,
        deposit_root: Root,
        deposit_count: Uint64,
    });
    pub const AggregateAndProof = ssz.VariableContainerType(struct {
        aggregator_index: ValidatorIndex,
        aggregate: Attestation,
        selection_proof: BLSSignature,
    });
    pub const SignedAggregateAndProof = ssz.VariableContainerType(struct {
        message: AggregateAndProof,
        signature: BLSSignature,
    });
    pub const ExecutionBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.EXECUTION_PAYLOAD_GINDEX), .{});
    pub const LightClientHeader = ssz.VariableContainerType(struct {
        beacon: BeaconBlockHeader,
        execution: ExecutionPayloadHeader,
        execution_branch: ExecutionBranch,
    });
    pub const CurrentSyncCommitteeBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.CURRENT_SYNC_COMMITTEE_GINDEX_ELECTRA), .{});
    pub const LightClientBootstrap = ssz.VariableContainerType(struct {
        header: LightClientHeader,
        current_sync_committee: SyncCommittee,
        current_sync_committee_branch: CurrentSyncCommitteeBranch,
    });
    pub const NextSyncCommitteeBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.NEXT_SYNC_COMMITTEE_GINDEX_ELECTRA), .{});
    pub const FinalityBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.FINALIZED_ROOT_GINDEX_ELECTRA), .{});
    pub const LightClientUpdate = ssz.VariableContainerType(struct {
        attested_header: LightClientHeader,
        next_sync_committee: SyncCommittee,
        next_sync_committee_branch: NextSyncCommitteeBranch,
        finalized_header: LightClientHeader,
        finality_branch: FinalityBranch,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const LightClientFinalityUpdate = ssz.VariableContainerType(struct {
        attested_header: LightClientHeader,
        finalized_header: LightClientHeader,
        finality_branch: FinalityBranch,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const LightClientOptimisticUpdate = ssz.VariableContainerType(struct {
        attested_header: LightClientHeader,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const SyncCommitteeMessage = ssz.FixedContainerType(struct {
        slot: Slot,
        beacon_block_root: Root,
        validator_index: ValidatorIndex,
        signature: BLSSignature,
    });
    pub const SyncSubcommitteeBits = ssz.BitVectorType(@divFloor(preset.SYNC_COMMITTEE_SIZE, constants.SYNC_COMMITTEE_SUBNET_COUNT));
    pub const SyncCommitteeContribution = ssz.FixedContainerType(struct {
        slot: Slot,
        beacon_block_root: Root,
        subcommittee_index: Uint64,
        aggregation_bits: SyncSubcommitteeBits,
        signature: BLSSignature,
    });
    pub const ContributionAndProof = ssz.FixedContainerType(struct {
        aggregator_index: ValidatorIndex,
        contribution: SyncCommitteeContribution,
        selection_proof: BLSSignature,
    });
    pub const SignedContributionAndProof = ssz.FixedContainerType(struct {
        message: ContributionAndProof,
        signature: BLSSignature,
    });
    pub const SyncAggregatorSelectionData = ssz.FixedContainerType(struct {
        slot: Slot,
        subcommittee_index: Uint64,
    });
    pub const VersionedHash = Bytes32;
    pub const VersionedHashes = ssz.FixedListType(VersionedHash, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const NewPayloadRequest = ssz.VariableContainerType(struct {
        execution_payload: ExecutionPayload,
        versioned_hashes: VersionedHashes,
        parent_beacon_block_root: Root,
        execution_requests: ExecutionRequests,
    });
    pub const PowBlock = ssz.FixedContainerType(struct {
        block_hash: Hash32,
        parent_hash: Hash32,
        total_difficulty: Uint256,
    });
    pub const BlobIndex = Uint64;
    pub const Blob = ssz.ByteVectorType((constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_BLOB));
    pub const KZGProof = Bytes48;
    pub const KZGCommitmentInclusionProof = ssz.FixedVectorType(Bytes32, preset.KZG_COMMITMENT_INCLUSION_PROOF_DEPTH, .{});
    pub const BlobSidecar = ssz.FixedContainerType(struct {
        index: BlobIndex,
        blob: Blob,
        kzg_commitment: KZGCommitment,
        kzg_proof: KZGProof,
        signed_block_header: SignedBeaconBlockHeader,
        kzg_commitment_inclusion_proof: KZGCommitmentInclusionProof,
    });
    pub const BlobIdentifier = ssz.FixedContainerType(struct {
        block_root: Root,
        index: BlobIndex,
    });
    pub const SingleAttestation = ssz.FixedContainerType(struct {
        committee_index: CommitteeIndex,
        attester_index: ValidatorIndex,
        data: AttestationData,
        signature: BLSSignature,
    });
    pub const ColumnIndex = Uint64;
    pub const Cell = ssz.ByteVectorType((constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_CELL));
    pub const DataColumn = ssz.FixedListType(Cell, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const KZGProofs = ssz.FixedListType(KZGProof, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const KZGCommitmentsInclusionProof = ssz.FixedVectorType(Bytes32, preset.KZG_COMMITMENTS_INCLUSION_PROOF_DEPTH, .{});
    pub const DataColumnSidecar = ssz.VariableContainerType(struct {
        index: ColumnIndex,
        column: DataColumn,
        kzg_commitments: BlobKZGCommitments,
        kzg_proofs: KZGProofs,
        signed_block_header: SignedBeaconBlockHeader,
        kzg_commitments_inclusion_proof: KZGCommitmentsInclusionProof,
    });
    pub const RowIndex = Uint64;
    pub const MatrixEntry = ssz.FixedContainerType(struct {
        cell: Cell,
        kzg_proof: KZGProof,
        column_index: ColumnIndex,
        row_index: RowIndex,
    });
    pub const DataColumnIndices = ssz.FixedListType(ColumnIndex, preset_module.NUMBER_OF_COLUMNS, .{});
    pub const DataColumnsByRootIdentifier = ssz.VariableContainerType(struct {
        block_root: Root,
        columns: DataColumnIndices,
    });
    pub const CellsBitList = ssz.BitListType(preset.MAX_BLOB_COMMITMENTS_PER_BLOCK);
    pub const PartialDataColumnHeader = ssz.VariableContainerType(struct {
        kzg_commitments: BlobKZGCommitments,
        signed_block_header: SignedBeaconBlockHeader,
        kzg_commitments_inclusion_proof: KZGCommitmentsInclusionProof,
    });
    pub const OptionalPartialDataColumnHeader = ssz.VariableListType(PartialDataColumnHeader, 1);
    pub const PartialDataColumnSidecar = ssz.VariableContainerType(struct {
        cells_present_bitmap: CellsBitList,
        partial_column: DataColumn,
        kzg_proofs: KZGProofs,
        header: OptionalPartialDataColumnHeader,
    });
    pub const PartialDataColumnPartsMetadata = ssz.VariableContainerType(struct {
        available: CellsBitList,
        requests: CellsBitList,
    });
    pub const PartialDataColumnGroupID = ssz.FixedContainerType(struct {
        beacon_block_root: Root,
    });
    const api = @import("beacon_api.zig").Types(@This(), true);
    pub const BeaconBlockContents = api.BeaconBlockContents;
    pub const SignedBeaconBlockContents = api.SignedBeaconBlockContents;
    pub const BlindedBeaconBlockBody = api.BlindedBeaconBlockBody;
    pub const BlindedBeaconBlock = api.BlindedBeaconBlock;
    pub const SignedBlindedBeaconBlock = api.SignedBlindedBeaconBlock;
};
pub const gloas = struct {
    pub const Bytes4 = ssz.ByteVectorType(4);
    pub const Version = Bytes4;
    pub const Uint64 = ssz.UintType(64);
    pub const Epoch = Uint64;
    pub const Fork = ssz.FixedContainerType(struct {
        previous_version: Version,
        current_version: Version,
        epoch: Epoch,
    });
    pub const Bytes32 = ssz.ByteVectorType(32);
    pub const Root = Bytes32;
    pub const ForkData = ssz.FixedContainerType(struct {
        current_version: Version,
        genesis_validators_root: Root,
    });
    pub const Checkpoint = ssz.FixedContainerType(struct {
        epoch: Epoch,
        root: Root,
    });
    pub const Bytes48 = ssz.ByteVectorType(48);
    pub const BLSPubkey = Bytes48;
    pub const Gwei = Uint64;
    pub const Boolean = ssz.BoolType();
    pub const Validator = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        effective_balance: Gwei,
        slashed: Boolean,
        activation_eligibility_epoch: Epoch,
        activation_epoch: Epoch,
        exit_epoch: Epoch,
        withdrawable_epoch: Epoch,
    });
    pub const Slot = Uint64;
    pub const CommitteeIndex = Uint64;
    pub const AttestationData = ssz.FixedContainerType(struct {
        slot: Slot,
        index: CommitteeIndex,
        beacon_block_root: Root,
        source: Checkpoint,
        target: Checkpoint,
    });
    pub const ValidatorIndex = Uint64;
    pub const AttestingIndices = ssz.FixedProgressiveListType(ValidatorIndex, .{});
    pub const Bytes96 = ssz.ByteVectorType(96);
    pub const BLSSignature = Bytes96;
    pub const IndexedAttestation = ssz.VariableProgressiveContainerType(struct {
        attesting_indices: AttestingIndices,
        data: AttestationData,
        signature: BLSSignature,
    }, &([_]u1{1} ** 3));
    pub const AggregationBits = ssz.ProgressiveBitListType(.{});
    pub const PendingAttestation = ssz.VariableContainerType(struct {
        aggregation_bits: AggregationBits,
        data: AttestationData,
        inclusion_delay: Slot,
        proposer_index: ValidatorIndex,
    });
    pub const Hash32 = Bytes32;
    pub const Eth1Data = ssz.FixedContainerType(struct {
        deposit_root: Root,
        deposit_count: Uint64,
        block_hash: Hash32,
    });
    pub const BlockRoots = ssz.FixedVectorType(Root, preset.SLOTS_PER_HISTORICAL_ROOT, .{});
    pub const StateRoots = ssz.FixedVectorType(Root, preset.SLOTS_PER_HISTORICAL_ROOT, .{});
    pub const HistoricalBatch = ssz.FixedContainerType(struct {
        block_roots: BlockRoots,
        state_roots: StateRoots,
    });
    pub const DepositMessage = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
    });
    pub const DepositData = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
    });
    pub const BeaconBlockHeader = ssz.FixedContainerType(struct {
        slot: Slot,
        proposer_index: ValidatorIndex,
        parent_root: Root,
        state_root: Root,
        body_root: Root,
    });
    pub const Domain = Bytes32;
    pub const SigningData = ssz.FixedContainerType(struct {
        object_root: Root,
        domain: Domain,
    });
    pub const SignedBeaconBlockHeader = ssz.FixedContainerType(struct {
        message: BeaconBlockHeader,
        signature: BLSSignature,
    });
    pub const ProposerSlashing = ssz.FixedContainerType(struct {
        signed_header_1: SignedBeaconBlockHeader,
        signed_header_2: SignedBeaconBlockHeader,
    });
    pub const AttesterSlashing = ssz.VariableContainerType(struct {
        attestation_1: IndexedAttestation,
        attestation_2: IndexedAttestation,
    });
    pub const CommitteeBits = ssz.BitVectorType(preset.MAX_COMMITTEES_PER_SLOT);
    pub const Attestation = ssz.VariableProgressiveContainerType(struct {
        aggregation_bits: AggregationBits,
        data: AttestationData,
        signature: BLSSignature,
        committee_bits: CommitteeBits,
    }, &([_]u1{1} ** 4));
    pub const DepositProof = ssz.FixedVectorType(Bytes32, (constants.DEPOSIT_CONTRACT_TREE_DEPTH + 1), .{});
    pub const Deposit = ssz.FixedContainerType(struct {
        proof: DepositProof,
        data: DepositData,
    });
    pub const VoluntaryExit = ssz.FixedContainerType(struct {
        epoch: Epoch,
        validator_index: ValidatorIndex,
    });
    pub const ProposerSlashings = ssz.FixedProgressiveListType(ProposerSlashing, .{});
    pub const AttesterSlashings = ssz.VariableProgressiveListType(AttesterSlashing, .{});
    pub const Attestations = ssz.VariableProgressiveListType(Attestation, .{});
    pub const Deposits = ssz.FixedProgressiveListType(Deposit, .{});
    pub const SignedVoluntaryExit = ssz.FixedContainerType(struct {
        message: VoluntaryExit,
        signature: BLSSignature,
    });
    pub const VoluntaryExits = ssz.FixedProgressiveListType(SignedVoluntaryExit, .{});
    pub const SyncCommitteeBits = ssz.BitVectorType(preset.SYNC_COMMITTEE_SIZE);
    pub const SyncAggregate = ssz.FixedContainerType(struct {
        sync_committee_bits: SyncCommitteeBits,
        sync_committee_signature: BLSSignature,
    });
    pub const Bytes20 = ssz.ByteVectorType(20);
    pub const ExecutionAddress = Bytes20;
    pub const BLSToExecutionChange = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        from_bls_pubkey: BLSPubkey,
        to_execution_address: ExecutionAddress,
    });
    pub const SignedBLSToExecutionChange = ssz.FixedContainerType(struct {
        message: BLSToExecutionChange,
        signature: BLSSignature,
    });
    pub const BLSToExecutionChanges = ssz.FixedProgressiveListType(SignedBLSToExecutionChange, .{});
    pub const BuilderIndex = Uint64;
    pub const KZGCommitment = Bytes48;
    pub const BlobKZGCommitments = ssz.FixedProgressiveListType(KZGCommitment, .{});
    pub const ExecutionPayloadBid = ssz.VariableProgressiveContainerType(struct {
        parent_block_hash: Hash32,
        parent_block_root: Root,
        block_hash: Hash32,
        prev_randao: Bytes32,
        fee_recipient: ExecutionAddress,
        gas_limit: Uint64,
        builder_index: BuilderIndex,
        slot: Slot,
        value: Gwei,
        execution_payment: Gwei,
        blob_kzg_commitments: BlobKZGCommitments,
        execution_requests_root: Root,
    }, &([_]u1{1} ** 12));
    pub const SignedExecutionPayloadBid = ssz.VariableContainerType(struct {
        message: ExecutionPayloadBid,
        signature: BLSSignature,
    });
    pub const PayloadTimelinessCommitteeBits = ssz.BitVectorType(preset.PTC_SIZE);
    pub const PayloadAttestationData = ssz.FixedContainerType(struct {
        beacon_block_root: Root,
        slot: Slot,
        payload_present: Boolean,
        blob_data_available: Boolean,
    });
    pub const PayloadAttestation = ssz.FixedProgressiveContainerType(struct {
        aggregation_bits: PayloadTimelinessCommitteeBits,
        data: PayloadAttestationData,
        signature: BLSSignature,
    }, &([_]u1{1} ** 3));
    pub const PayloadAttestations = ssz.FixedProgressiveListType(PayloadAttestation, .{});
    pub const DepositRequest = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
        index: Uint64,
    });
    pub const DepositRequests = ssz.FixedProgressiveListType(DepositRequest, .{});
    pub const WithdrawalRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        validator_pubkey: BLSPubkey,
        amount: Gwei,
    });
    pub const WithdrawalRequests = ssz.FixedProgressiveListType(WithdrawalRequest, .{});
    pub const ConsolidationRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        source_pubkey: BLSPubkey,
        target_pubkey: BLSPubkey,
    });
    pub const ConsolidationRequests = ssz.FixedProgressiveListType(ConsolidationRequest, .{});
    pub const BuilderDepositRequest = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
    });
    pub const BuilderDepositRequests = ssz.FixedProgressiveListType(BuilderDepositRequest, .{});
    pub const BuilderExitRequest = ssz.FixedContainerType(struct {
        source_address: ExecutionAddress,
        pubkey: BLSPubkey,
    });
    pub const BuilderExitRequests = ssz.FixedProgressiveListType(BuilderExitRequest, .{});
    pub const ExecutionRequests = ssz.VariableProgressiveContainerType(struct {
        deposits: DepositRequests,
        withdrawals: WithdrawalRequests,
        consolidations: ConsolidationRequests,
        builder_deposits: BuilderDepositRequests,
        builder_exits: BuilderExitRequests,
    }, &([_]u1{1} ** 5));
    pub const BeaconBlockBody = ssz.VariableProgressiveContainerType(struct {
        randao_reveal: BLSSignature,
        eth1_data: Eth1Data,
        graffiti: Bytes32,
        proposer_slashings: ProposerSlashings,
        attester_slashings: AttesterSlashings,
        attestations: Attestations,
        deposits: Deposits,
        voluntary_exits: VoluntaryExits,
        sync_aggregate: SyncAggregate,
        bls_to_execution_changes: BLSToExecutionChanges,
        signed_execution_payload_bid: SignedExecutionPayloadBid,
        payload_attestations: PayloadAttestations,
        parent_execution_requests: ExecutionRequests,
    }, &([_]u1{1} ** 13));
    pub const BeaconBlock = ssz.VariableContainerType(struct {
        slot: Slot,
        proposer_index: ValidatorIndex,
        parent_root: Root,
        state_root: Root,
        body: BeaconBlockBody,
    });
    pub const HistoricalRoots = ssz.FixedListType(Root, preset.HISTORICAL_ROOTS_LIMIT, .{});
    pub const Eth1DataVotes = ssz.FixedListType(Eth1Data, (preset.EPOCHS_PER_ETH1_VOTING_PERIOD * preset.SLOTS_PER_EPOCH), .{});
    pub const Validators = ssz.FixedProgressiveListType(Validator, .{});
    pub const Balances = ssz.FixedProgressiveListType(Gwei, .{});
    pub const RandaoMixes = ssz.FixedVectorType(Bytes32, preset.EPOCHS_PER_HISTORICAL_VECTOR, .{});
    pub const Slashings = ssz.FixedVectorType(Gwei, preset.EPOCHS_PER_SLASHINGS_VECTOR, .{});
    pub const Uint8 = ssz.UintType(8);
    pub const ParticipationFlags = Uint8;
    pub const EpochParticipation = ssz.FixedProgressiveListType(ParticipationFlags, .{});
    pub const JustificationBits = ssz.BitVectorType(constants.JUSTIFICATION_BITS_LENGTH);
    pub const InactivityScores = ssz.FixedProgressiveListType(Uint64, .{});
    pub const SyncCommitteePubkeys = ssz.FixedVectorType(BLSPubkey, preset.SYNC_COMMITTEE_SIZE, .{});
    pub const SyncCommittee = ssz.FixedContainerType(struct {
        pubkeys: SyncCommitteePubkeys,
        aggregate_pubkey: BLSPubkey,
    });
    pub const WithdrawalIndex = Uint64;
    pub const HistoricalSummary = ssz.FixedContainerType(struct {
        block_summary_root: Root,
        state_summary_root: Root,
    });
    pub const HistoricalSummaries = ssz.FixedListType(HistoricalSummary, preset.HISTORICAL_ROOTS_LIMIT, .{});
    pub const PendingDeposit = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        withdrawal_credentials: Bytes32,
        amount: Gwei,
        signature: BLSSignature,
        slot: Slot,
    });
    pub const PendingDeposits = ssz.FixedProgressiveListType(PendingDeposit, .{});
    pub const PendingPartialWithdrawal = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        amount: Gwei,
        withdrawable_epoch: Epoch,
    });
    pub const PendingPartialWithdrawals = ssz.FixedProgressiveListType(PendingPartialWithdrawal, .{});
    pub const PendingConsolidation = ssz.FixedContainerType(struct {
        source_index: ValidatorIndex,
        target_index: ValidatorIndex,
    });
    pub const PendingConsolidations = ssz.FixedProgressiveListType(PendingConsolidation, .{});
    pub const ProposerLookahead = ssz.FixedVectorType(ValidatorIndex, ((preset.MIN_SEED_LOOKAHEAD + 1) * preset.SLOTS_PER_EPOCH), .{});
    pub const Builder = ssz.FixedContainerType(struct {
        pubkey: BLSPubkey,
        version: Uint8,
        execution_address: ExecutionAddress,
        balance: Gwei,
        deposit_epoch: Epoch,
        withdrawable_epoch: Epoch,
    });
    pub const Builders = ssz.FixedProgressiveListType(Builder, .{});
    pub const ExecutionPayloadAvailability = ssz.BitVectorType(preset.SLOTS_PER_HISTORICAL_ROOT);
    pub const BuilderPendingWithdrawal = ssz.FixedContainerType(struct {
        fee_recipient: ExecutionAddress,
        amount: Gwei,
        builder_index: BuilderIndex,
    });
    pub const BuilderPendingPayment = ssz.FixedContainerType(struct {
        weight: Gwei,
        withdrawal: BuilderPendingWithdrawal,
        proposer_index: ValidatorIndex,
    });
    pub const BuilderPendingPayments = ssz.FixedVectorType(BuilderPendingPayment, (2 * preset.SLOTS_PER_EPOCH), .{});
    pub const BuilderPendingWithdrawals = ssz.FixedProgressiveListType(BuilderPendingWithdrawal, .{});
    pub const Withdrawal = ssz.FixedContainerType(struct {
        index: WithdrawalIndex,
        validator_index: ValidatorIndex,
        address: ExecutionAddress,
        amount: Gwei,
    });
    pub const Withdrawals = ssz.FixedProgressiveListType(Withdrawal, .{});
    pub const PayloadTimelinessCommittee = ssz.FixedVectorType(ValidatorIndex, preset.PTC_SIZE, .{});
    pub const PayloadTimelinessCommitteeWindow = ssz.FixedVectorType(PayloadTimelinessCommittee, ((preset.MIN_SEED_LOOKAHEAD + 2) * preset.SLOTS_PER_EPOCH), .{});
    pub const BeaconState = ssz.VariableProgressiveContainerType(struct {
        genesis_time: Uint64,
        genesis_validators_root: Root,
        slot: Slot,
        fork: Fork,
        latest_block_header: BeaconBlockHeader,
        block_roots: BlockRoots,
        state_roots: StateRoots,
        historical_roots: HistoricalRoots,
        eth1_data: Eth1Data,
        eth1_data_votes: Eth1DataVotes,
        eth1_deposit_index: Uint64,
        validators: Validators,
        balances: Balances,
        randao_mixes: RandaoMixes,
        slashings: Slashings,
        previous_epoch_participation: EpochParticipation,
        current_epoch_participation: EpochParticipation,
        justification_bits: JustificationBits,
        previous_justified_checkpoint: Checkpoint,
        current_justified_checkpoint: Checkpoint,
        finalized_checkpoint: Checkpoint,
        inactivity_scores: InactivityScores,
        current_sync_committee: SyncCommittee,
        next_sync_committee: SyncCommittee,
        latest_block_hash: Hash32,
        next_withdrawal_index: WithdrawalIndex,
        next_withdrawal_validator_index: ValidatorIndex,
        historical_summaries: HistoricalSummaries,
        deposit_requests_start_index: Uint64,
        deposit_balance_to_consume: Gwei,
        exit_balance_to_consume: Gwei,
        earliest_exit_epoch: Epoch,
        consolidation_balance_to_consume: Gwei,
        earliest_consolidation_epoch: Epoch,
        pending_deposits: PendingDeposits,
        pending_partial_withdrawals: PendingPartialWithdrawals,
        pending_consolidations: PendingConsolidations,
        proposer_lookahead: ProposerLookahead,
        builders: Builders,
        next_withdrawal_builder_index: BuilderIndex,
        execution_payload_availability: ExecutionPayloadAvailability,
        builder_pending_payments: BuilderPendingPayments,
        builder_pending_withdrawals: BuilderPendingWithdrawals,
        latest_execution_payload_bid: ExecutionPayloadBid,
        payload_expected_withdrawals: Withdrawals,
        ptc_window: PayloadTimelinessCommitteeWindow,
    }, &([_]u1{1} ** 46));
    pub const SignedBeaconBlock = ssz.VariableContainerType(struct {
        message: BeaconBlock,
        signature: BLSSignature,
    });
    pub const Eth1Block = ssz.FixedContainerType(struct {
        timestamp: Uint64,
        deposit_root: Root,
        deposit_count: Uint64,
    });
    pub const AggregateAndProof = ssz.VariableContainerType(struct {
        aggregator_index: ValidatorIndex,
        aggregate: Attestation,
        selection_proof: BLSSignature,
    });
    pub const SignedAggregateAndProof = ssz.VariableContainerType(struct {
        message: AggregateAndProof,
        signature: BLSSignature,
    });
    pub const ExecutionBranch = ssz.FixedVectorType(Bytes32, std.math.log2(2856), .{});
    pub const LightClientHeader = ssz.FixedContainerType(struct {
        beacon: BeaconBlockHeader,
        execution_block_hash: Hash32,
        execution_branch: ExecutionBranch,
    });
    pub const CurrentSyncCommitteeBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.CURRENT_SYNC_COMMITTEE_GINDEX_GLOAS), .{});
    pub const LightClientBootstrap = ssz.FixedContainerType(struct {
        header: LightClientHeader,
        current_sync_committee: SyncCommittee,
        current_sync_committee_branch: CurrentSyncCommitteeBranch,
    });
    pub const NextSyncCommitteeBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.NEXT_SYNC_COMMITTEE_GINDEX_GLOAS), .{});
    pub const FinalityBranch = ssz.FixedVectorType(Bytes32, std.math.log2(constants.FINALIZED_ROOT_GINDEX_GLOAS), .{});
    pub const LightClientUpdate = ssz.FixedContainerType(struct {
        attested_header: LightClientHeader,
        next_sync_committee: SyncCommittee,
        next_sync_committee_branch: NextSyncCommitteeBranch,
        finalized_header: LightClientHeader,
        finality_branch: FinalityBranch,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const LightClientFinalityUpdate = ssz.FixedContainerType(struct {
        attested_header: LightClientHeader,
        finalized_header: LightClientHeader,
        finality_branch: FinalityBranch,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const LightClientOptimisticUpdate = ssz.FixedContainerType(struct {
        attested_header: LightClientHeader,
        sync_aggregate: SyncAggregate,
        signature_slot: Slot,
    });
    pub const SyncCommitteeMessage = ssz.FixedContainerType(struct {
        slot: Slot,
        beacon_block_root: Root,
        validator_index: ValidatorIndex,
        signature: BLSSignature,
    });
    pub const SyncSubcommitteeBits = ssz.BitVectorType(@divFloor(preset.SYNC_COMMITTEE_SIZE, constants.SYNC_COMMITTEE_SUBNET_COUNT));
    pub const SyncCommitteeContribution = ssz.FixedContainerType(struct {
        slot: Slot,
        beacon_block_root: Root,
        subcommittee_index: Uint64,
        aggregation_bits: SyncSubcommitteeBits,
        signature: BLSSignature,
    });
    pub const ContributionAndProof = ssz.FixedContainerType(struct {
        aggregator_index: ValidatorIndex,
        contribution: SyncCommitteeContribution,
        selection_proof: BLSSignature,
    });
    pub const SignedContributionAndProof = ssz.FixedContainerType(struct {
        message: ContributionAndProof,
        signature: BLSSignature,
    });
    pub const SyncAggregatorSelectionData = ssz.FixedContainerType(struct {
        slot: Slot,
        subcommittee_index: Uint64,
    });
    pub const LogsBloom = ssz.ByteVectorType(preset.BYTES_PER_LOGS_BLOOM);
    pub const ExtraData = ssz.ByteListType(preset.MAX_EXTRA_DATA_BYTES);
    pub const Uint256 = ssz.UintType(256);
    pub const Byte = ssz.UintType(8);
    pub const Transaction = ssz.ProgressiveByteListType(.{});
    pub const Transactions = ssz.VariableProgressiveListType(Transaction, .{});
    pub const BlockAccessList = ssz.ProgressiveByteListType(.{});
    pub const ExecutionPayload = ssz.VariableProgressiveContainerType(struct {
        parent_hash: Hash32,
        fee_recipient: ExecutionAddress,
        state_root: Bytes32,
        receipts_root: Bytes32,
        logs_bloom: LogsBloom,
        prev_randao: Bytes32,
        block_number: Uint64,
        gas_limit: Uint64,
        gas_used: Uint64,
        timestamp: Uint64,
        extra_data: ExtraData,
        base_fee_per_gas: Uint256,
        block_hash: Hash32,
        transactions: Transactions,
        withdrawals: Withdrawals,
        blob_gas_used: Uint64,
        excess_blob_gas: Uint64,
        block_access_list: BlockAccessList,
        slot_number: Uint64,
    }, &([_]u1{1} ** 19));
    pub const ExecutionPayloadHeader = ssz.VariableContainerType(struct {
        parent_hash: Hash32,
        fee_recipient: ExecutionAddress,
        state_root: Bytes32,
        receipts_root: Bytes32,
        logs_bloom: LogsBloom,
        prev_randao: Bytes32,
        block_number: Uint64,
        gas_limit: Uint64,
        gas_used: Uint64,
        timestamp: Uint64,
        extra_data: ExtraData,
        base_fee_per_gas: Uint256,
        block_hash: Hash32,
        transactions_root: Root,
        withdrawals_root: Root,
        blob_gas_used: Uint64,
        excess_blob_gas: Uint64,
    });
    pub const VersionedHash = Bytes32;
    pub const VersionedHashes = ssz.FixedListType(VersionedHash, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    pub const NewPayloadRequest = ssz.VariableProgressiveContainerType(struct {
        execution_payload: ExecutionPayload,
        versioned_hashes: VersionedHashes,
        parent_beacon_block_root: Root,
        execution_requests: ExecutionRequests,
    }, &([_]u1{1} ** 4));
    pub const PowBlock = ssz.FixedContainerType(struct {
        block_hash: Hash32,
        parent_hash: Hash32,
        total_difficulty: Uint256,
    });
    pub const BlobIndex = Uint64;
    pub const Blob = ssz.ByteVectorType((constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_BLOB));
    pub const KZGProof = Bytes48;
    pub const KZGCommitmentInclusionProof = ssz.FixedVectorType(Bytes32, preset.KZG_COMMITMENT_INCLUSION_PROOF_DEPTH, .{});
    pub const BlobSidecar = ssz.FixedContainerType(struct {
        index: BlobIndex,
        blob: Blob,
        kzg_commitment: KZGCommitment,
        kzg_proof: KZGProof,
        signed_block_header: SignedBeaconBlockHeader,
        kzg_commitment_inclusion_proof: KZGCommitmentInclusionProof,
    });
    pub const BlobIdentifier = ssz.FixedContainerType(struct {
        block_root: Root,
        index: BlobIndex,
    });
    pub const SingleAttestation = ssz.FixedContainerType(struct {
        committee_index: CommitteeIndex,
        attester_index: ValidatorIndex,
        data: AttestationData,
        signature: BLSSignature,
    });
    pub const ColumnIndex = Uint64;
    pub const Cell = ssz.ByteVectorType((constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_CELL));
    pub const DataColumn = ssz.FixedProgressiveListType(Cell, .{});
    pub const KZGProofs = ssz.FixedProgressiveListType(KZGProof, .{});
    pub const DataColumnSidecar = ssz.VariableContainerType(struct {
        index: ColumnIndex,
        column: DataColumn,
        kzg_proofs: KZGProofs,
        slot: Slot,
        beacon_block_root: Root,
    });
    pub const RowIndex = Uint64;
    pub const MatrixEntry = ssz.FixedContainerType(struct {
        cell: Cell,
        kzg_proof: KZGProof,
        column_index: ColumnIndex,
        row_index: RowIndex,
    });
    pub const DataColumnIndices = ssz.FixedListType(ColumnIndex, preset_module.NUMBER_OF_COLUMNS, .{});
    pub const DataColumnsByRootIdentifier = ssz.VariableContainerType(struct {
        block_root: Root,
        columns: DataColumnIndices,
    });
    pub const CellsBitList = ssz.ProgressiveBitListType(.{});
    pub const PartialDataColumnSidecar = ssz.VariableContainerType(struct {
        cells_present_bitmap: CellsBitList,
        partial_column: DataColumn,
        kzg_proofs: KZGProofs,
    });
    pub const PartialDataColumnPartsMetadata = ssz.VariableContainerType(struct {
        available: CellsBitList,
        requests: CellsBitList,
    });
    pub const KZGCommitmentsInclusionProof = ssz.FixedVectorType(Bytes32, preset.KZG_COMMITMENTS_INCLUSION_PROOF_DEPTH, .{});
    pub const PartialDataColumnHeader = ssz.VariableContainerType(struct {
        kzg_commitments: BlobKZGCommitments,
        signed_block_header: SignedBeaconBlockHeader,
        kzg_commitments_inclusion_proof: KZGCommitmentsInclusionProof,
    });
    pub const PartialDataColumnGroupID = ssz.FixedContainerType(struct {
        beacon_block_root: Root,
        slot: Slot,
    });
    pub const PayloadAttestationMessage = ssz.FixedContainerType(struct {
        validator_index: ValidatorIndex,
        data: PayloadAttestationData,
        signature: BLSSignature,
    });
    pub const PayloadTimelinessCommitteeIndices = ssz.FixedListType(ValidatorIndex, preset.PTC_SIZE, .{});
    pub const IndexedPayloadAttestation = ssz.VariableProgressiveContainerType(struct {
        attesting_indices: PayloadTimelinessCommitteeIndices,
        data: PayloadAttestationData,
        signature: BLSSignature,
    }, &([_]u1{1} ** 3));
    pub const ExecutionPayloadEnvelope = ssz.VariableProgressiveContainerType(struct {
        payload: ExecutionPayload,
        execution_requests: ExecutionRequests,
        builder_index: BuilderIndex,
        beacon_block_root: Root,
        parent_beacon_block_root: Root,
    }, &([_]u1{1} ** 5));
    pub const SignedExecutionPayloadEnvelope = ssz.VariableContainerType(struct {
        message: ExecutionPayloadEnvelope,
        signature: BLSSignature,
    });
    pub const ProposerPreferences = ssz.FixedContainerType(struct {
        dependent_root: Root,
        proposal_slot: Slot,
        validator_index: ValidatorIndex,
        fee_recipient: ExecutionAddress,
        target_gas_limit: Uint64,
    });
    pub const SignedProposerPreferences = ssz.FixedContainerType(struct {
        message: ProposerPreferences,
        signature: BLSSignature,
    });
};
